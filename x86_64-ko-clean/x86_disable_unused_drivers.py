#!/usr/bin/python3

# x86_disable_unused_drivers.py "Kate Hsuan" "hpa@redhat.com"
#
# Automatically disable the driver which is not required by x86
#
# Usage:
# 1. Create a JSON file in redhat/scripts/x86_allow folder.
# 2. Run the script in the root of the kernel source tree.
# redhat/scripts/x86_disable_unused_drivers.py "Committer" "committer@example.com"

import argparse
import jinja2
import json
import sys
import os
import re
import shutil

from git import Repo
from git import config
from git import Git

ALLOW_PATH = "redhat/scripts/x86_allow"

'''
The allow list files are placed in redhat/scripts/x86_allow folder.
The config file in x86 folder is used to disable the driver and
the example in JSON format is shown below:

{
  "name": "iio_accel",
  "driver_path": "drivers/iio/accel/",
  "redhat_config_path": "redhat/configs/fedora/generic",
  "redhat_x86_config_path": "redhat/configs/fedora/generic/x86",
  "allow_list": ["CONFIG_BMC150_ACCEL_I2C",
                 "CONFIG_DA280",
                 "CONFIG_HID_SENSOR_ACCEL_3D",
                 "CONFIG_KXCJK1013",
                 "CONFIG_MMA7660",
                 "CONFIG_MMA8452",
                 "CONFIG_MXC4005",
                 "CONFIG_MXC6255",
                 "CONFIG_IIO_ST_ACCEL_I2C_3AXIS",
                 "CONFIG_IIO_ST_ACCEL_3AXIS",
                 "CONFIG_BMC150_ACCEL"
                 ],
  "commit_msg": "Disable {{ config_name }} because the chip this driver is for is not used on any x86 boards."
}

{{ config_name }} is the config name in Kconfig file and it will replaced by Jinja.

'''

class GitManager:
    def __init__(self, committer, email, teardown=False):
        self.committer = committer
        self.email = email
        self.teardown = teardown
        self.environment = jinja2.Environment()

        try:
            path = os.getcwd()
            self.repo = Repo(path)
            self.git_obj = Git(path)
        except Exception as e:
            print(e)
            sys.exit(1)

        # switch to working branch
        try:
            branch = self.repo.active_branch
            self.base_branch = branch.name
            self.repo.git.checkout(b="wip/driver/unused_iio_accel")
        except Exception as e:
            print(e)
            sys.exit(1)

    def commit_patch(self, redhat_config_x86_path:str, file:str, commit_template:str):
        last_commit = None

        # get the last commit of the repo
        for commit in self.repo.iter_commits():
            last_commit = commit
            break

        self.repo.index.add([os.path.join(redhat_config_x86_path, file)])
        template = self.environment.from_string(commit_template)
        replaced_msg = template.render(config_name=file)

        commit_msg = ("Disable {}\n\n"
                     "{}\n\n"
                      "Signed-off-by: {}<{}>".format(file,
                                                     replaced_msg,
                                                     self.committer,
                                                     self.email))
        self.repo.index.commit(commit_msg)

        git_path = shutil.which("git")
        self.git_obj.execute([git_path, "format-patch", last_commit.hexsha])

    def teardown_branch(self):
        self.repo.git.checkout(self.base_branch)
        self.repo.git.branch("-D", "wip/driver/unused_iio_accel")


def disable_driver(file:str, redhat_config_path:str, redhat_x86_config_path:str):
    valid = re.compile(file+"=m|y")
    with open(os.path.join(redhat_config_path, file), "r+") as f:
        lines = f.readlines()
        # match the first line of the config.
        # if the config is set, we create a CONFIG_ file in x86 folder
        # to disable the driver.
        if valid.match(lines[0]):
            with open(os.path.join(redhat_x86_config_path, file), "w") as x86:
                x86.write("# "+file+" is not set\n")

def get_kconfig(driver_path:str, redhat_config_path:str):
    config_list = []

    valid = re.compile("^config [A-Z0-9]+(_[A-Z0-9]*)*")
    with open(os.path.join(driver_path, "Kconfig")) as f:
        config = f.readlines()
        for line in config:
            if valid.match(line):
                config_list.append("CONFIG_"+line[7:-1])

    print("Kconfig are found in {}:".format(driver_path))
    for file in config_list:
        if os.path.isfile(os.path.join(redhat_config_path, file)):
            print(file)

    return config_list

def is_required(file, allow_list):
    if file in allow_list:
        return True
    else:
        return False
    
def list_allow():
    allow_files = []
    path = os.getcwd()
    scan_files = os.scandir(os.path.join(path, ALLOW_PATH))
    #scan_files = os.scandir('/opt/allow_list')

    for i in scan_files:
        if (os.path.isfile(i.path)):
            allow_files.append(i.path)

    return allow_files

def config_clean(gitobj, driver_path:str, redhat_config_path:str,
                 x86_redhat_config_path:str, allow_list:list, commit_template:str):
    kconfig = get_kconfig(driver_path, redhat_config_path)

    print("Start to scan the config files.")
    for file in os.listdir(redhat_config_path):
       if os.path.isfile(os.path.join(redhat_config_path, file)) and file in kconfig:
           if is_required(file, allow_list) == False:
               print("{} is not required.".format(file))
               disable_driver(file, redhat_config_path, x86_redhat_config_path)
               gitobj.commit_patch(x86_redhat_config_path, file, commit_template)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("committer", help="Committer name")
    parser.add_argument("email", help="Committer email")
    parser.add_argument("--teardown",
                        help="Delete the working branch (wip/driver/unused_iio_accel)",
                        action="store_true")
    args = parser.parse_args()

    gitobj = GitManager(args.committer, args.email, args.teardown)

    allow_files = list_allow()

    for file in allow_files:
        name = None
        driver_path = None
        redhat_config_path = None
        redhat_x86_config_path = None
        allow_list = None
        print(file)
        with open(file, "r") as json_file:
            try:
                json_data = json.load(json_file)
                name = json_data["name"]
                driver_path = json_data["driver_path"]
                redhat_config_path = json_data["redhat_config_path"]
                redhat_x86_config_path = json_data["redhat_x86_config_path"]
                allow_list = json_data["allow_list"]
                commit_msg = json_data["commit_msg"]
                print("Driver catalog name: {}".format(name))
                print("Driver path: {}".format(driver_path))
                print("Red Hat config path: {}".format(redhat_config_path))
                print("Red Hat x86 config path: {}".format(redhat_x86_config_path))
            except Exception as e:
                print("Error: ignore incorrect allow file.")
                continue

        config_clean(gitobj, driver_path, redhat_config_path,
                     redhat_x86_config_path, allow_list, commit_msg)

    #teardown the working branch
    if args.teardown:
        gitobj.teardown_branch()

if __name__ == "__main__":
    main()
