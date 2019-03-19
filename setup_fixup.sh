#! /bin/bash

set -o xtrace

SERVICE_FILE="./workarounds/ksz9897r-rev.A1-fixup.service"
FIXUP_FILE="./workarounds/ksz9897r-rev.A1-fixup.py"
SERVICE_DST_DIR="/etc/systemd/system/"
FIXUP_DST_DIR="/etc/ksz9787_revA1_fixup"

check_or_install_pkg() {
    local required_pkg=$1

    local pkg_ok=$(dpkg-query -W --showformat='${Status}\n' ${required_pkg} | grep "install ok installed")
    echo Checking for ${required_pkg}: $pkg_ok

    if [ "" == "$pkg_ok" ]; then
        echo "No ${required_pkg}. Installing required dependecy."
        apt-get --force-yes --yes install ${required_pkg}
    fi
}

check_or_setup_fixup_service() {
    local service_path=$1
    local fixup_path=$2
    local service_dst_dir=$3
    local fixup_dst_dir=$4
    local service_file=$(basename -- "${service_path}")
    local fixup_file=$(basename -- "${fixup_path}")

    local status=$(systemctl list-unit-files | grep ${service_file} | awk '{print $2}')

    if [ "" == "${status}" ]; then

        echo "${service_file} does not exit. Installing service."

        # install service unit file
        cp ${service_file} ${service_dst_dir}
        systemctl enable ${service_file}

        # install fixup sciript in known place
        mkdir -p ${fixup_dst_dir}
        cp ${fixup_script} ${fixup_dst_dir}
        chmod +x ${fixup_dst_dir}/${fixup_file}

        echo "${service_file} is installed. Reboot is required to apply it."
    elif [ "disabled" == "$status" ]; then
        echo "${service_file} is disabled. Enable service."
        systemctl enable ${service_file}
        echo "${service_file} is enabled. Reboot is required to apply it."
    else
        echo "${service_file} is enabled"
    fi
}

if ! [ $(id -u) = 0 ]; then
    echo "run script as root"
    exit 1
fi

if ! [ -d "workarounds" ]; then
    echo "run script from git root directory"
    exit 1
fi

# install required dependecy
check_or_install_pkg "i2c-tools"

# setup systemd service to apply workaround of each boot
# and before network service
check_or_setup_fixup_service $SERVICE_FILE $FIXUP_FILE $SERVICE_DST_DIR $FIXUP_DST_DIR

