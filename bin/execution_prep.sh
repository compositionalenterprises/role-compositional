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
        -p | --playvaultpass
                REQUIRED
                The play's vault password
        -b | --branch
                OPTIONAL
                DEFAULT: 'master'
                The branch (or tag) to use for role-compositional
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
                        -b | --branch )
                                shift
                                branch="${1}"
                                ;;
                        -y | --playbranch )
                                shift
                                playbranch="${1}"
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

if [[ -z "${branch}" ]]; then
        branch='master'
fi
if [[ -z "${playbranch}" ]]; then
        playbranch='master'
fi

# Clone into the unique job exec id for this run
git clone --branch ${playbranch} --single-branch \
        https://gitlab.com/compositionalenterprises/play-compositional.git "${jobuuid}"
cd "${jobuuid}"

# General setup and refactor setting the vault pass before the final if statement
sed -i "s/version: master/version: ${branch}/" 'requirements.yml'
echo "${playvaultpass}" > .vault_pass

if [[ -z "${envvaultpass}" ]]; then
        >&2 echo "No Environment Vault Password Specified, Skipping Environment Clone."
else
        >&2 echo "Cloning the environment repo..."
        #
        # Clone the environment down giving the domain we're working on
        # The domain should be coming in looking like `client.ourcompose.com` or `andrewcz.com`
        # We also want to insert in the vault pass at this time too.
        #
        # It's been failing lately, so we're putting it in this "until" loop so that we keep trying
        # and sleeping until we're able to successfully clone it.
        #
        environment_domain=$(sed 's/\./-/g' <<<"${domain}")
        until [[ ${env_clone_result:=1} != 1 ]]; do
                >&2 echo "Trying to clone the environment..."
                git clone --depth 1 --single-branch --branch ${environment_domain} \
                                git@gitlab.com:compositionalenterprises/environment && \
                        env_clone_result=0 || env_clone_result=1

                if [[ ${env_clone_result:=1} == 1 ]]; then
                        >&2 echo "Could not clone environment repo!!! Taking a quick nap..."
                        sleep $[ ( $RANDOM % 20 )  + 10 ]s
                        >&2 echo "Trying to clone the environment repo again..."
                fi
        done
        # TODO: Make this a URL call somewhere in the future.
        echo "${envvaultpass}" > environment/.vault_pass

        #
        # Here we are overridding/setting the branch that we pass in to Portal if we get it
        # passed from Rundeck
        #
        # We want to override if:
        #       - Rundeck branch != branch that is the environment branch, as long as that
        #         passed-in Rundeck branch != master, since master would be the default everywhere
        #         so at that point, why bother?
        #
        # We do NOT to override if:
        #       - The environment does not have compositional_portal_role_branch defined. This
        #         would automatically default to master. AND... if the Rundeck branch passed in
        #         is master, it just skips the override, so the default (master) kicks in.
        #       - The Rundeck branch == 'master', in which case, we'll just let the default kick
        #         in, and let it run its course. This is _even_ when what is defined in the env
        #         is different from what is passed in. Since passing in 'master' from Rundeck is
        #         the default, we want to set the illusion that we default to the environment, even
        #         though what is passed in is 'master'. And FWIW, we should never be passing in
        #         'master' in production environments. So worse case scenario, we set up a dev env
        #         to default to a specific branch in the env, and then run comp role and pass it
        #         'master' from Rundeck, and expect it to take 'master'. Since this is a stupid
        #         mistake to make, we won't take it into account here.
        #
        # This _does_ mean that we have to determine whether the environment contains that variable
        if ! grep 'compositional_portal_role_branch' \
                        ./environment/group_vars/compositional/all.yml; then
                # If it doesn't, then let's pre-emptivly just put it in there and exit
                >&2 echo "Setting '${branch}' as role branch for ${domain}"
                echo "compositional_portal_role_branch: ${branch}" >> \
                        ./environment/group_vars/compositional/all.yml
        # Here we are actually overriding it temporarily. This is in the case when Rundeck passed
        # in a branch that was other than master, but did not match the one that was set in the
        # environment for this domain. We won't change the actual environment, since we wouldn't
        # be pushing the repo back up in this situation (unless it is a migration). So we will
        # consider this to be a temporary override.
        elif [[ ${branch} != 'master' && \
                ${branch} != $(grep 'compositional_portal_role_branch' \
                                        ./environment/group_vars/compositional/all.yml | \
                                cut -d ' ' -f 2) ]]; then
                >&2 echo "Temporarily using '${branch}' as role branch for ${domain}"
                sed -i "s/compositional_portal_role_branch:.*/compositional_portal_role_branch: ${branch}/" \
                        './environment/group_vars/compositional/all.yml'
        # If we've got here, then we've been able to find the role branch variable. We've also
        # determined that the passed-in branch is either master, or the exact same as what is
        # defined in the environment, so we just leave well-enough alone.
        else
                >&2 echo "Leaving compositional_portal_role_branch as: \
                        $(grep 'compositional_portal_role_branch' \
                                ./environment/group_vars/compositional/all.yml)"
        fi
fi
