import os
from pathlib import Path
from django.core.management.templates import TemplateCommand
import shutil
class Command(TemplateCommand):
    def add_arguments(self, parser):
        pass

    def handle(self, **options):
        old_path = self.handle_template(None, 'project_template/lambda_function.py-tpl')
        shutil.copy(old_path, Path(os.getcwd(), 'lambda_function.py'))
