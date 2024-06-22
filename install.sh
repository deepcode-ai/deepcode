#!/bin/bash

set -e
err_report() {
    echo "Error on line $1"
    echo "Fail to install deepcode"
}
trap 'err_report $LINENO' ERR

usage() {
  echo """
Usage: install.sh [options...]

By default will install deepcode and all third party dependecies accross all machines listed in
hostfile (hostfile: /job/hostfile). If no hostfile exists, will only install locally

[optional]
    -d, --deepcode_only    Install only deepcode and no third party dependencies
    -t, --third_party_only  Install only third party dependencies and not deepcode
    -l, --local_only        Installs only on local machine
    -h, --help              This help text
  """
}

dc_only=0
tp_only=0
deepcode_install=1
third_party_install=1
local_only=0
entire_dlts_job=1

while [[ $# -gt 0 ]]
do
key="$1"
case $key in
    -d|--deepcode_only)
    deepcode_install=1;
    third_party_install=0;
    dc_only=1;
    shift
    ;;
    -t|--third_party_only)
    deepcode_install=0;
    third_party_install=1;
    tp_only=1;
    shift
    ;;
    -l|--local_only)
    local_only=1;
    shift
    ;;
    -h|--help)
    usage
    exit 0
    ;;
    *)
    echo "Unkown argument(s)"
    usage
    exit 1
    shift
    ;;
esac
done

if [ "$dc_only" == "1" ] && [ "$tp_only" == "1" ]; then
    echo "-d and -t are mutually exclusive, only choose one or none"
    usage
    exit 1
fi

echo "Updating git hash/branch info"
echo "git_hash = '$(git rev-parse --short HEAD)'" > deepcode/version_info.py
echo "git_branch = '$(git rev-parse --abbrev-ref HEAD)'" >> deepcode/version_info.py
cat deepcode/version_info.py

install_apex='sudo -H pip install -v --no-cache-dir --global-option="--cpp_ext" --global-option="--cuda_ext" third_party/apex'

if [ ! -f /job/hostfile ]; then
        echo "No hostfile exists at /job/hostfile, installing locally"
        local_only=1
fi

if [ "$local_only" == "1" ]; then
    if [ "$third_party_install" == "1" ]; then
        echo "Checking out sub-module(s)"
        git submodule update --init --recursive

        echo "Building apex wheel"
        cd third_party/apex
        python setup.py --cpp_ext --cuda_ext bdist_wheel
        cd -

        echo "Installing apex"
        sudo -H pip uninstall -y apex
        sudo -H pip install third_party/apex/dist/apex*.whl
    fi
    if [ "$deepcode_install" == "1" ]; then
        echo "Installing deepcode"
        python setup.py bdist_wheel
        sudo -H pip uninstall -y deepcode
        sudo -H pip install dist/deepcode*.whl

        python -c 'import deepcode; print("deepcode info:", deepcode.__version__, deepcode.__git_branch__, deepcode.__git_hash__)'
        echo "Installation is successful"
    fi
else
    local_path=`pwd`
    hostfile=/job/hostfile
    if [ -f $hostfile ]; then
        hosts=`cat $hostfile | awk '{print $1}' | paste -sd "," -`;
    else
        echo "hostfile not found, cannot proceed"
        exit 1
    fi
    export PDSH_RCMD_TYPE=ssh;

    if [ "$third_party_install" == "1" ]; then
        echo "Checking out sub-module(s)"
        git submodule update --init --recursive

        echo "Installing apex"
        cd third_party/apex
        python setup.py --cpp_ext --cuda_ext bdist_wheel
        cd -
        pdsh -w $hosts "sudo -H pip uninstall -y apex"
        pdsh -w $hosts "cd $local_path; sudo -H pip install third_party/apex/dist/apex*.whl"
        pdsh -w $hosts 'python -c "import apex"'
    fi
    if [ "$deepcode_install" == "1" ]; then
        echo "Installing deepcode"
        python setup.py bdist_wheel
        pdsh -w $hosts "sudo -H pip uninstall -y deepcode"
        pdsh -w $hosts "cd $local_path; sudo -H pip install dist/deepcode*.whl"
        pdsh -w $hosts "python -c 'import deepcode; print(\"deepcode info:\", deepcode.__version__, deepcode.__git_branch__, deepcode.__git_hash__)'"
        echo "Installation is successful"
    fi
fi
