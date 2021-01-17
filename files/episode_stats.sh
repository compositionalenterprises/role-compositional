#!/bin/bash
entries=$(docker logs proxy 2>/dev/null | grep 'jekyll.*mp3' | grep 'GET' | cut -d ' ' -f 1,4,7,12-)

while IFS= read -r entry; do
        episode="$(echo ${entry} | cut -d ' ' -f 3 | rev | cut -d '/' -f 1 | rev | cut -d '.' -f 1)"
        ip="$(echo ${entry} | cut -d ' ' -f 1)"
        user_agent="$(echo ${entry} | cut -d '"' -f 2)"

        orig_date="$(echo ${entry} | cut -d '[' -f 2 | cut -d ':' -f 1)"
        orig_day="$(echo ${orig_date} | cut -d '/' -f 1)"
        orig_year="$(echo ${orig_date} | cut -d '/' -f 3)"
        case "$(echo ${orig_date} | cut -d '/' -f 2)" in
                'Jan')
                        orig_month='01'
                        ;;
                'Feb')
                        orig_month='02'
                        ;;
                'Mar')
                        orig_month='03'
                        ;;
                'Apr')
                        orig_month='04'
                        ;;
                'May')
                        orig_month='05'
                        ;;
                'Jun')
                        orig_month='06'
                        ;;
                'Jul')
                        orig_month='07'
                        ;;
                'Aug')
                        orig_month='08'
                        ;;
                'Sep')
                        orig_month='08'
                        ;;
                'Oct')
                        orig_month='10'
                        ;;
                'Nov')
                        orig_month='11'
                        ;;
                'Dec')
                        orig_month='12'
                        ;;
        esac

        if [[ ! -f /srv/local/nginx_episode_stats/${episode}.log ]]; then
                touch /srv/local/nginx_episode_stats/${episode}.log
        fi

        if ! grep -qR "${orig_year}${orig_month}${orig_day},${ip},${user_agent}" /srv/local/nginx_episode_stats/${episode}.log; then
                echo "Putting ${user_agent} into ${episode}"
                echo "${orig_year}${orig_month}${orig_day},${ip},${user_agent}" >> /srv/local/nginx_episode_stats/${episode}.log
        fi

done <<< "${entries}"
