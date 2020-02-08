#!/bin/bash
set -e

function usage() {
        cat << EOF
Usage:
        $ ${0} [OPTION] ...

Options:
        -j | --jobuuid
                REQUIRED
                A unique ID for this run
        -d | --domain
                REQUIRED
                The domain to of the environment
        -e | --envvaultpass
                REQUIRED
                The environment's vault password
        -p | --playsvaultpass
                REQUIRED
                The play's vault password
        -h | --help
                OPTIONAL
                Show this usage message and exit
EOF
}

while [[ "${1}" != "" ]]; do
        if [[ "${1}" =~ '-' ]]; then
                # Check for flags
                case "${1}" in
                        -j | --jobuuid )
                                shift
                                jobuuid="${1}"
                                ;;
                        -d | --domain )
                                shift
                                domain="${1}"
                                ;;
                        -p | --playvaultpass )
                                shift
                                playvaultpass="${1}"
                                ;;
                        -e | --envvaultpass )
                                shift
                                envvaultpass="${1}"
                                ;;
                        -h | --help )
                                usage
                                exit
                                ;;
                        * )
                                >&2 echo "Invalid Argument: \'${1}\'"
                                usage
                                exit 2
                esac
        else
                >&2 echo "Unknown Positional Argument: \'${1}\'"
                usage
                exit 3
        fi
        shift
done

# Make sure the necessary vars are defined
if [[ -z "${jobuuid}" ]]; then
        >&2 echo "No Job UUID Specified"
        usage
        exit 5
elif [[ -z "${domain}" ]]; then
        >&2 echo "No Domain Specified"
        usage
        exit 6
elif [[ -z "${playvaultpass}" ]]; then
        >&2 echo "No Play Vault Password Specified"
        usage
        exit 7
fi

# Clone into the unique job exec id for this run
git clone https://gitlab.com/compositionalenterprises/play-compositional.git "${jobuuid}"
cd "${jobuuid}"

if [[ -z "${envvaultpass}" ]]; then
        >&2 echo "No Environment Vault Password Specified, Skipping Environment Clone"
else
        # Clone the environment down giving the domain we're working on
        # The domain should be coming in looking like `client.ourcompose.com` or `andrewcz.com`
        # We also want to insert in the vault pass at this time too.
        environment_domain=$(sed 's/\./-/g' <<<"${domain}")
        >&2 echo "git clone ${environment_domain} git@gitlab.com:compositionalenterprises/environment.git environment"
        git clone --depth 1 --single-branch --branch ${environment_domain} git@gitlab.com:compositionalenterprises/environment
        # TODO: Make this a URL call somewhere in the future.
        echo "${envvaultpass}" > environment/.vault_pass
fi
echo "${playvaultpass}" > .vault_pass
