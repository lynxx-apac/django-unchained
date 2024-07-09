from pathlib import Path
from django.core.management import BaseCommand
import shutil
import boto3
import subprocess
import zipfile
import os


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--region', type=str, help='AWS region to deploy to',
                            default='ap-southeast-2')
        parser.add_argument('--packages', type=bool, help='Download packages',
                            default=False)

    def handle(self, *args, **options):
        region = options['region'] or input("Enter the AWS region to deploy to: ")
        packages = options['packages']
        project_name = Path.cwd().name.replace('_', '-')
        self.stdout.write(f"Deploying project: {project_name}")
        ec2 = boto3.client('ec2', region_name=region)
        vpcs = ec2.describe_vpcs()['Vpcs']
        self.stdout.write("Available VPCs:")
        for i, vpc in enumerate(vpcs):
            self.stdout.write(
                f"{i + 1}. {vpc['VpcId']} ({vpc.get('Tags', [{'Key': 'Name', 'Value': 'Unnamed'}])[0]['Value']})")
        vpc_index = int(input("Enter the number of the VPC to use: ")) - 1
        vpc_id = vpcs[vpc_index]['VpcId']
        security_groups = ec2.describe_security_groups(
            Filters=[
                {'Name': 'vpc-id', 'Values': [vpc_id]},
                {'Name': 'group-name', 'Values': ['default']}
            ]
        )['SecurityGroups']
        if not security_groups:
            self.stderr.write(
                self.style.ERROR(f"No default security group found for VPC {vpc_id}"))
            return
        security_group_id = security_groups[0]['GroupId']
        self.stdout.write(f"Using default security group: {security_group_id}")
        subnets = ec2.describe_subnets(
            Filters=[{'Name': 'vpc-id', 'Values': [vpc_id]}])['Subnets']
        self.stdout.write("\nAvailable Subnets:")
        for i, subnet in enumerate(subnets):
            self.stdout.write(
                f"{i + 1}. {subnet['SubnetId']} ({subnet.get('Tags', [{'Key': 'Name', 'Value': 'Unnamed'}])[0]['Value']})")
        subnet_indices = input(
            "Enter the numbers of the subnets to use (comma-separated): ").split(',')
        subnet_ids = [subnets[int(i.strip()) - 1]['SubnetId'] for i in subnet_indices]

        django_layer_path = Path('django_layer/python')
        django_layer_path.mkdir(parents=True, exist_ok=True)
        self.stdout.write('Installing Django and dependencies...')
        if packages:
            if django_layer_path.exists():
                shutil.rmtree(django_layer_path)
            subprocess.run([
                'pip', 'install',
                '-t', str(django_layer_path),
                '-r', 'requirements.txt',
                '--platform', 'manylinux2014_x86_64', '--only-binary=:all:'
            ], check=True)
            shutil.rmtree(Path(django_layer_path, 'rest_framework'))
            subprocess.run([
                'pip', 'install',
                '-t', str(django_layer_path),
                '--upgrade', '-I',
                '../django-unchained'
            ], check=True)
        self.stdout.write('Creating deployment package...')
        exclude_dirs = {'.venv', 'venv', '__pycache__', '.idea', 'django_layer',
                        '.aws-sam', '.git', 'frontend'}
        exclude_files = {'db.sqlite3', 'lambda-package.zip'}
        with zipfile.ZipFile('lambda-package.zip', 'w') as zf:
            for root, dirs, files in os.walk('.'):
                for exclude_dir in exclude_dirs:
                    if exclude_dir in dirs:
                        dirs.remove(exclude_dir)
                for file in files:
                    if file.endswith('.pyc') or file in exclude_files:
                        continue
                    path = os.path.join(root, file)
                    zf.write(path, path[2:])

        self.stdout.write('Deploying with SAM...')
        subprocess.run(['sam', 'build'], check=True)
        subprocess.run([
            'sam', 'deploy', '--guided',
            '--stack-name', f'django-unchained-{project_name}-stack',
            '--parameter-overrides',
            f'VpcId={vpc_id}',
            f'SubnetIds={",".join(subnet_ids)}',
            f'SecurityGroupId={security_group_id}',
            f'ProjectName={project_name}'
        ], check=True)
        Path('lambda-package.zip').unlink()
        self.stdout.write(self.style.SUCCESS('Deployment completed successfully!'))
