#!/bin/bash

function system_sshd_edit_bool {
    # $1 - param name
    # $2 - Yes/No
    VALUE=`lower $2`
    if [ "$VALUE" == "yes" ] || [ "$VALUE" == "no" ]; then
        sed -i "s/^#*\($1\).*/\1 $VALUE/" /etc/ssh/sshd_config
    fi
}

function system_sshd_permitrootlogin {
    system_sshd_edit_bool "PermitRootLogin" "$1"
}

function system_sshd_passwordauthentication {
    system_sshd_edit_bool "PasswordAuthentication" "$1"
}

function system_add_user {
    # $1 - username
    # $2 - password
    # $3 - groups
    USERNAME=`lower $1`
    PASSWORD=$2
    SUDO_GROUP=$3
    SHELL="/bin/bash"
    useradd --create-home --shell "$SHELL" --user-group --groups "$SUDO_GROUP" "$USERNAME"
    echo "$USERNAME:$PASSWORD" | chpasswd
}

function system_add_system_user {
    # $1 - username
    # $2 - home
    USERNAME=`lower $1`
    HOME_DIR=$2
    if [ -z "$HOME_DIR" ]; then
        useradd --system --no-create-home --user-group $USERNAME
    else
        useradd --system --no-create-home --home-dir "$HOME_DIR" --user-group $USERNAME
    fi;
}

function system_update_hostname {
    # $1 - system hostname
    if [ ! -n "$1" ]; then
        echo "system_update_hostname() requires the system hostname as its first argument"
        return 1;
    fi
    echo $1 > /etc/hostname
    hostname -F /etc/hostname
    echo -e "\n127.0.0.1 $1.local $1\n" >> /etc/hosts
}
