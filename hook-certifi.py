# PyInstaller hook for certifi
from PyInstaller.utils.hooks import copy_metadata, collect_data_files

datas = collect_data_files('certifi')

# Ensure certifi metadata is included
copy_metadata('certifi')
