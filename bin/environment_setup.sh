#!/bin/bash
set -e

function usage() {
        cat << EOF
Usage:
        $ ${0} [OPTION] ...

Options:
        -i | --jobexecid
                REQUIRED
                The ID of the job execution
        -d | --domain
                REQUIRED
                The domain to of the environment
        -v | --vaultpass
                REQUIRED
                The vault password
        -h | --help
                Optional
                Show this usage message and exit
EOF
}

while [[ "${1}" != "" ]]; do
        if [[ "${1}" =~ '-' ]]; then
                # Check for flags
                case "${1}" in
                        -i | --jobexecid )
                                shift
                                jobexecid="${1}"
                                ;;
                        -d | --domain )
                                shift
                                domain="${1}"
                                ;;
                        -v | --vaultpass )
                                shift
                                vaultpass="${1}"
                                ;;
                        -h | --help )
                                usage
                                exit
                                ;;
                        * )
                                usage
                                exit 2
                esac
        else
                usage
                exit 3
        fi
        shift
done

# Make sure the necessary vars are defined
if [[ -z "${jobexecid}" ]]; then
        usage
        exit 5
elif [[ -z "${domain}" ]]; then
        usage
        exit 6
elif [[ -z "${vaultpass}" ]]; then
        usage
        exit 7
fi

# Clone into the unique job exec id for this run
git clone https://gitlab.com/smacz/play-compositional.git "${jobexecid}"
cd "${jobexecid}"

# Clone the environment down giving the domain we're working on
# The domain should be coming in looking like `client.ourcompose.com` or `andrewcz.com`
# We also want to insert in the vault pass at this time too.
environment_domain=$(sed 's/\./_/g' <<<"${domain}")
git clone https://gitlab.com/smacz/environment-"${environment_domain}".git environment
# TODO: Make this a URL call somewhere in the future.
echo "${vaultpass}" > environment/.vault_pass
