#!/bin/bash
#
# Trigger an event or notification upon the output of a command


PROGRAM="${0##*/}"
CONFIG="$HOME/.config/scripts/${PROGRAM%.*}/triggers.conf"
DEFAULT_TRIGGER='notify-send --icon=notification-message-im --urgency=critical "triggerd: $EVENT_NAME" "We have a trigger event!"'


eventlog(){
    # Usage: eventlog WARNING "${event[FILENAME]}" "message"
    loghandler "[$2]" "$1" "$3"
}

load_event(){
    unset event
    declare -gA event
    event[triggered]=false
    event[FILENAME]=${event_file##*/}
    while IFS= read -r line; do
        local parameter=${line%%=*}
        local value=${line#*=}
        [[ -n $parameter && -n $value ]] && event["$parameter"]="$value"
    done < "$event_file"
}

logger(){
    # Usage: logger WARNING "message"
    loghandler "($PROGRAM)" "$1" "$2"
}

loghandler(){
    if [[ $2 = ERROR ]]; then
        loglevel=40
    elif [[ $2 = WARNING ]]; then
        loglevel=30
    elif [[ $2 = INFO ]]; then
        loglevel=20
    elif [[ $2 = DEBUG ]]; then
        loglevel=10
    fi

    if [[ $option_verbose = true ]]; then
        setlevel=20
    else
        setlevel=30
    fi

    if (( loglevel >= setlevel )); then
        echo "$1 $2: $3" >&2
    fi
}

prepare_trigger(){
    # allow us to use $EVENT_NAME rather than ${event[EVENT_NAME]} in custom/defined triggers
    unset EVENT_NAME
    EVENT_NAME=${event[EVENT_NAME]}

    if [[ -n ${event[TRIGGER_CUSTOM]} ]]; then
        event[trigger]=${event[TRIGGER_CUSTOM]}
    elif [[ -n ${event[TRIGGER_NAMED]} ]]; then
        if [[ ! -f $CONFIG ]]; then
            logger ERROR "TRIGGER_NAMED must be defined in '$CONFIG'"
        elif [[ ! -r $CONFIG ]]; then
            logger ERROR "No read access to '$CONFIG'"
        else
            if hash bash-config 2>/dev/null; then
                event[trigger]=$(bash-config "$CONFIG" "${event[TRIGGER_NAMED]}" 2>/dev/null)
            else
                event[trigger]=$(sed -n "s/^${event[TRIGGER_NAMED]}\ *=\ *//p" "$CONFIG" 2>/dev/null)
            fi

            if [[ -z ${event[trigger]} ]]; then
                eventlog WARNING "${event[FILENAME]}" "TRIGGER_NAMED '${event[TRIGGER_NAMED]}' is not defined in '$CONFIG'"
            fi
        fi
    fi

    if [[ -z ${event[trigger]} ]]; then
        eventlog WARNING "${event[FILENAME]}" "No trigger configured (will use default)"
        trigger_type=default
        event[trigger]=$DEFAULT_TRIGGER
    fi
}

verify_event(){
    local errors=0
    local missing=()

    [[ -z ${event[MATCH_CONTENT]} && ! ${event[MATCH_CRITERIA]} =~ ^(null|not_null)$ ]] && missing+=(MATCH_CONTENT)

    for element in COMMAND EVENT_NAME MATCH_CRITERIA STATUS TEST_TYPE; do
        [[ -z ${event[$element]} ]] && missing+=($element)
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        eventlog ERROR "${event[FILENAME]}" "Missing ${missing[@]}"
        ((++errors))
    fi

    if [[ -n ${event[TEST_TYPE]} && ! ${event[TEST_TYPE]} =~ ^(arithmetic|content|status)$ ]]; then
        eventlog ERROR "${event[FILENAME]}" "Invalid TEST_TYPE"
        ((++errors))
    fi

    if [[ ${event[TEST_TYPE]} =~ ^(arithmetic|status)$ ]]; then
        if [[ -n ${event[MATCH_CONTENT]} && ! ${event[MATCH_CONTENT]} =~ ^-?[0-9]+$ ]]; then
            eventlog ERROR "${event[FILENAME]}" "MATCH_CONTENT must be an integer for arithmetic operations"
            ((++errors))
        fi
        if [[ -n ${event[MATCH_CRITERIA]} && ! ${event[MATCH_CRITERIA]} =~ ^(eq|ge|gt|le|lt|ne)$ ]]; then
            eventlog ERROR "${event[FILENAME]}" "Invalid MATCH_CRITERIA for arithmetic operations"
            ((++errors))
        fi
    fi

    if [[ ${event[TEST_TYPE]} = content && -n ${event[MATCH_CRITERIA]} && ! ${event[MATCH_CRITERIA]} =~ ^(contains|does_not_contain|matches|does_not_match|null|not_null)$ ]]; then
        eventlog ERROR "${event[FILENAME]}" "Invalid MATCH_CRITERIA for content operations"
        ((++errors))
    fi

    if [[ -n ${event[TRIGGER_CUSTOM]} && -n ${event[TRIGGER_NAMED]} ]]; then
        eventlog ERROR "${event[FILENAME]}" "TRIGGER_CUSTOM and TRIGGER_NAMED are both indicated (choose one or neither)"
        ((++errors))
    fi

    if (( errors == 1 )); then
        eventlog WARNING "${event[FILENAME]}" "Encountered 1 issue verifying event file"
        return 1
    elif (( errors >= 2 )); then
        eventlog WARNING "${event[FILENAME]}" "Encountered $errors issues verifying event file"
        return 1
    fi
}


if (( $# == 0 )); then
    logger ERROR "Please indicate target event files and/or directories"
    logger ERROR "Try '$PROGRAM --help' for more information."
    exit 1
elif (( $# == 1 )) && [[ $1 =~ ^(-h|--help)$ ]]; then
    echo "Usage: $PROGRAM <event files|folders>"
    echo "Trigger an event or notification upon the output of a command."
    echo
    echo "  --verbose              show event execution details"
    echo "  --verify               verify event files without execution"
    exit 0
fi

events=()
for arg in "${@}"; do
    if [[ $arg = --verbose ]]; then
        option_verbose=true
    elif [[ $arg = --verify ]]; then
        option_verify=true
    elif [[ -f $arg ]]; then
        events+=("$arg")
    elif [[ -d $arg ]]; then
        if [[ -r $arg ]]; then
            while IFS= read -r line; do
                events+=("$line")
            done < <(find "$arg" \( -empty -name '.*' -prune \) -o \( -name '*.conf' -o -name '*.txt' -print -type f -writable \))
        else
            logger ERROR "Skipping '$arg' directory (no read access)"
        fi
    fi
done

if (( ${#events[@]} == 0 )); then
    logger ERROR "You have not supplied any valid targets"
    exit 1
fi

logger INFO "processing ${#events[@]} events"

for event_file in "${events[@]}"; do

    load_event

    if [[ $option_verify = true ]]; then
        eventlog INFO "${event[FILENAME]}" "Verifying only"
        option_verbose=true
        if verify_event; then
            eventlog INFO "${event[FILENAME]}" "Verification OK"
        else
            eventlog INFO "${event[FILENAME]}" "Verification NOT OK"
        fi
        option_verbose=false
        prepare_trigger
        continue
    elif [[ ${event[STATUS]} != enabled ]]; then
        eventlog INFO "${event[FILENAME]}" "Not enabled (skipping)"
        continue
    elif ! verify_event; then
        eventlog INFO "${event[FILENAME]}" "Failed verification (skipping)"
        continue
    fi

    # execute event command
    event[command_output]=$(eval "${event[COMMAND]}" 2>/dev/null)
    event[exit]=$?

    # compare command output with match content (per match criteria)
    if [[ ${event[TEST_TYPE]} = arithmetic ]]; then
        if [[ ${event[command_output]} =~ ^-?[0-9]+$ ]] && eval [[ ${event[command_output]} -${event[MATCH_CRITERIA]} ${event[MATCH_CONTENT]} ]]; then
            event[triggered]=true
        fi
    elif [[ ${event[TEST_TYPE]} = content ]]; then
        if [[ ${event[MATCH_CRITERIA]} = contains ]]; then
            grep -q "${event[MATCH_CONTENT]}" <<<"${event[command_output]}" &>/dev/null
            if (( $? == 0 )); then
                event[triggered]=true
            elif (( $? > 1 )); then
                eventlog ERROR "${event[FILENAME]}" "grep experienced an unknown error handling command output"
            fi
        elif [[ ${event[MATCH_CRITERIA]} = does_not_contain ]]; then
            grep -q "${event[MATCH_CONTENT]}" <<<"${event[command_output]}" &>/dev/null
            if (( $? == 1 )); then
                event[triggered]=true
            elif (( $? > 1 )); then
                eventlog ERROR "${event[FILENAME]}" "grep experienced an unknown error handling command output"
            fi
        elif [[ ${event[MATCH_CRITERIA]} = matches ]]; then
            [[ ${event[command_output]} = "${event[MATCH_CONTENT]}" ]] && event[triggered]=true
        elif [[ ${event[MATCH_CRITERIA]} = does_not_match ]]; then
            [[ ${event[command_output]} != "${event[MATCH_CONTENT]}" ]] && event[triggered]=true
        elif [[ ${event[MATCH_CRITERIA]} = null ]]; then
            [[ -z ${event[command_output]} ]] && event[triggered]=true
        elif [[ ${event[MATCH_CRITERIA]} = not_null ]]; then
            [[ -n ${event[command_output]} ]] && event[triggered]=true
        fi
    elif [[ ${event[TEST_TYPE]} = status ]]; then
        if eval [[ ${event[exit]} -${event[MATCH_CRITERIA]} ${event[MATCH_CONTENT]} ]]; then
            event[triggered]=true
        fi
    fi

    eventlog INFO "${event[FILENAME]}" "Event execution details:"

    for index in "${!event[@]}"; do
        eventlog INFO "${event[FILENAME]}" "\${event[$index]}=${event[$index]}"
    done

    if [[ ${event[triggered]} != true ]]; then
        eventlog INFO "${event[FILENAME]}" "Trigger conditions not met"
        continue
    else
        eventlog INFO "${event[FILENAME]}" "Trigger conditions are met"
    fi

    prepare_trigger
    eval "${event[trigger]}" &>/dev/null

    if (( $? != 0 )) && [[ ${event[trigger_type]} != default ]]; then
        eventlog ERROR "${event[FILENAME]}" "Trigger event returned a nonzero exit code"
        eventlog ERROR "${event[FILENAME]}" "Executing default trigger..."
        eval "$DEFAULT_TRIGGER" &>/dev/null
    fi

    if hash bash-config 2>/dev/null; then
        bash-config "$event_file" STATUS triggered &>/dev/null
    else
        sed -i 's/STATUS=enabled/STATUS=triggered/;s/STATUS = enabled/STATUS = triggered/' "$event_file"
    fi

    if grep -Eq '(STATUS=triggered|STATUS = triggered)' "$event_file" &>/dev/null; then
        eventlog INFO "${event[FILENAME]}" "Event file STATUS successfully updated to triggered"
    else
        eventlog ERROR "${event[FILENAME]}" "Event file STATUS unsuccessfully updated to triggered!"
    fi
done
