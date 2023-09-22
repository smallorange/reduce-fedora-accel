#!/usr/bin/python3

import sys
import os
import re

ACCEL_PATH = "/home/kate/work/fedora_kernel/kernel-ark/drivers/iio/accel/"
ACCEL_CONFIG_PATH = "/home/kate/work/fedora_kernel/kernel-ark/redhat/configs/fedora/generic"
ACCEL_CONFIG_X86_64_PATH = "/home/kate/work/fedora_kernel/kernel-ark/redhat/configs/fedora/generic/x86"

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

def disable_driver(file):
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
    kconfig = get_accel_config()
 
    for file in os.listdir(ACCEL_CONFIG_PATH):
       if os.path.isfile(os.path.join(ACCEL_CONFIG_PATH, file)) and file in kconfig:
           if is_required(file) == False:
               print("{} is not required.".format(file))
               disable_driver(file)


if __name__ == "__main__":
    main()




