#!/usr/bin/python3

#./accel.py "Kate Hsuan" "hpa@redhat.com"
#
# Automatically disable the driver which is not required by x86
#
# Usage:
# Run the script in the root of the kernel source tree.
# redhat/scripts/accel.py "Committer" "committer@example.com"

import argparse
import sys
import os
import re
import shutil

from git import Repo
from git import config
from git import Git

ACCEL_PATH = "drivers/iio/accel/"
ACCEL_CONFIG_PATH = "redhat/configs/fedora/generic"
ACCEL_CONFIG_X86_64_PATH = "redhat/configs/fedora/generic/x86"
SOURCE_ROOT = "/home/kate/work/fedora_kernel/kernel-ark"

X86_64_ACCEL_ALLOW =["CONFIG_BMC150_ACCEL_I2C",
                     "CONFIG_DA280",
                     "CONFIG_HID_SENSOR_ACCEL_3D",
                     "CONFIG_KXCJK1013",
                     "CONFIG_MMA7660",
                     "CONFIG_MMA8452",
                     "CONFIG_MXC4005",
                     "CONFIG_MXC6255",
                     "CONFIG_IIO_ST_ACCEL_I2C_3AXIS",
                     "CONFIG_BMC150_ACCEL"
                     ]

class GitManager:
    def __init__(self, committer, email):
        self.committer = committer
        self.email = email

        try:
            path = os.getcwd()
            self.repo = Repo(path)
            self.git_obj = Git(path)
        except Exception as e:
            print(e)
            sys.exit(1)

        # switch to working branch
        try:
            self.repo.git.checkout(b="wip/driver/reduction")
        except Exception as e:
            print(e)
            sys.exit(1)

    def commit_patch(self, file:str):
        last_commit = None

        # get the last commit of the repo
        for commit in self.repo.iter_commits():
            last_commit = commit
            break

        self.repo.index.add([os.path.join(ACCEL_CONFIG_X86_64_PATH, file)])
        commit_msg = ("Disable {}\n\nSince {}\n"
                     "wasn't required by x86, it was disabled.\n\n"
                     "Singed-off-by: {}<{}>".format(file,
                                                    file,
                                                    self.committer,
                                                    self.email))
        self.repo.index.commit(commit_msg)

        git_path = shutil.which("git")
        self.git_obj.execute([git_path, "format-patch", last_commit.hexsha])


def disable_driver(file:str):
    valid = re.compile(file+"=m|y")
    with open(os.path.join(ACCEL_CONFIG_PATH, file), "r+") as f:
        lines = f.readlines()
        # match the first line of the config.
        # if the config is set, we create a CONFIG_ file in x86 folder
        # to disable the driver.
        if valid.match(lines[0]):
            with open(os.path.join(ACCEL_CONFIG_X86_64_PATH, file), "w") as x86:
            #with open(os.path.join("/tmp", file), "w") as x86:
                x86.write("# "+file+" is not set\n")

def get_accel_config():
    config_list = []

    valid = re.compile("^config [A-Z0-9]+(_[A-Z0-9]*)*")
    with open(os.path.join(ACCEL_PATH, "Kconfig")) as f:
        config = f.readlines()
        for line in config:
            if valid.match(line):
                config_list.append("CONFIG_"+line[7:-1])

    return config_list

def is_required(file):
    if file in X86_64_ACCEL_ALLOW:
        return True
    else:
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("committer", help="Committer name")
    parser.add_argument("email", help="Committer email")
    args = parser.parse_args()

    git_m = GitManager(args.committer, args.email)

    kconfig = get_accel_config()
    #repo = Repo(os.getcwd())

    for file in os.listdir(ACCEL_CONFIG_PATH):
       if os.path.isfile(os.path.join(ACCEL_CONFIG_PATH, file)) and file in kconfig:
           if is_required(file) == False:
               print("{} is not required.".format(file))
               disable_driver(file)
               git_m.commit_patch(file)

if __name__ == "__main__":
    main()
