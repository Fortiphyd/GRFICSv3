import os
import subprocess

from abc import ABC, abstractmethod


class Extension(ABC):

    @abstractmethod
    def __init__(self, files, dependencies=None, file_hooks=None):
        """Files is list of 2-tuples of the form (filename, package)"""
        self.files = files
        self.dependencies = dependencies if dependencies else []
        # Maps file name to async function that takes in file data, processes it, and returns processed output.
        self.file_hooks = file_hooks if file_hooks else dict()

    def check_go_dependencies(self, gocat_dir):
        """Returns True if the golang dependencies are met for this module, False if not."""
        for d in self.dependencies:
            dep_result = subprocess.run('go list "{}"'.format(d), shell=True, cwd=gocat_dir,
                                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            if (dep_result.stdout.decode()).strip() != d:
                return False
        return True

    async def copy_module_files(self, base_dir):
        """Copies module files into their corresponding location within the gocat directory.
        If a hook function is assigned to the file, run the hook function on the file data before
        copying it to the gocat directory.
        Returns True on success."""
        for file, pkg in self.files:
            # Make sure the package folders are there or are created.
            src_package_path = os.path.join(base_dir, 'gocat-extensions', pkg)
            dest_package_path = os.path.join(base_dir, 'gocat', pkg)
            if not os.path.exists(dest_package_path):
                os.makedirs(dest_package_path)

            # Check if entire package is to be copied
            if file == '*':
                await self._copy_folder_files(src_package_path, dest_package_path)
            else:
                await self._copy_file_with_hook(file, os.path.join(src_package_path, file),
                                                os.path.join(dest_package_path, file))
        return True

    def remove_module_files(self, base_dir):
        """Cleans up module-specific files from the gocat directory."""
        for file, pkg in self.files:
            package_path = os.path.join(base_dir, 'gocat', pkg)
            # Check if entire package is to be deleted
            if file == '*':
                self._unstage_folder(package_path)
            else:
                file_path = os.path.join(package_path, file)
                if os.path.exists(file_path):
                    os.remove(file_path)

    def install_dependencies(self):
        """Attempt to install all dependencies if they aren't fulfilled. Returns True on success, False otherwise."""
        return False

    async def _copy_folder_files(self, src_dir, dest_dir):
        """Copies files from src_dir to dest_dir. Not recursive. Assumes src_dir and dest_dir are absolute paths."""
        for dir_item in os.listdir(src_dir):
            src_path = os.path.join(src_dir, dir_item)
            if os.path.isfile(src_path):
                await self._copy_file_with_hook(dir_item, src_path, os.path.join(dest_dir, dir_item))

    async def _copy_file_with_hook(self, file_name, src_path, dest_path):
        with open(src_path, 'r') as src_file:
            data = src_file.read()
        if file_name in self.file_hooks:
            data = await self.file_hooks[file_name](data)
        with open(dest_path, 'w') as dest_file:
            dest_file.write(data)

    @staticmethod
    def _unstage_folder(dir_path):
        """Deletes files (except for load.go) from the directory at dir_path. Not recursive."""
        for dir_item in os.listdir(dir_path):
            full_path = os.path.join(dir_path, dir_item)
            if os.path.isfile(full_path) and dir_item != 'load.go':
                os.remove(full_path)


class ConfigFileException(Exception):
    """Raise this exception when a required variable or setting for the
    extension is not specified in the C2 configuration file"""
    pass
