#!/bin/bash
#
# Trigger an event or notification upon the output of a command


CONFIG="$HOME/.config/scripts/${0##*/}/triggers.conf"
DEFAULT_TRIGGER='notify-send --icon=notification-message-im --urgency=critical "triggerd: $EVENT_NAME" "We have a trigger event!"'


error(){
    echo "ERROR: $@" >&2
}

load_event(){
    unset event
    declare -gA event
    event[FILENAME]=${event_file##*/}
    while IFS= read -r line; do
        local parameter=$(grep -oP "^[A-Za-z0-9_-]+(?==)" <<< "$line")
        local value=$(sed -n "s/^${parameter}=//p" <<< "$line")
        [[ -n $parameter && -n $value ]] && event["$parameter"]="$value"
    done < "$event_file"
}

prepare_trigger(){
    # allow us to use $EVENT_NAME rather than ${event[EVENT_NAME]} in custom/defined triggers
    unset EVENT_NAME
    EVENT_NAME=${event[EVENT_NAME]}

    if [[ -n ${event[TRIGGER_CUSTOM]} ]]; then
        event[trigger]=${event[TRIGGER_CUSTOM]}
    elif [[ -n ${event[TRIGGER_NAMED]} ]]; then
        if [[ ! -f $CONFIG ]]; then
            warning "TRIGGER_NAMED must be defined in '$CONFIG'"
        elif [[ ! -r $CONFIG ]]; then
            warning "No read access to '$CONFIG'"
        else
            if hash bash-config 2>/dev/null; then
                event[trigger]=$(bash-config "$CONFIG" "${event[TRIGGER_NAMED]}" 2>/dev/null)
            else
                event[trigger]=$(sed -n "s/^${event[TRIGGER_NAMED]}\ *=\ *//p" "$CONFIG" 2>/dev/null)
            fi
            [[ -z ${event[trigger]} ]] && warning "TRIGGER_NAMED '${event[TRIGGER_NAMED]}' not defined in '$CONFIG' for '$event_file'"
        fi
    fi

    if [[ -z ${event[trigger]} ]]; then
        trigger_type=default
        event[trigger]=$DEFAULT_TRIGGER
        warning "Resorting to default trigger"
    fi
}

verify_event(){
    local flag_error
    local missing=()

    [[ -z ${event[MATCH_CONTENT]} && ! ${event[MATCH_CRITERIA]} =~ ^(null|not_null)$ ]] && missing+=(MATCH_CONTENT)

    for element in COMMAND EVENT_NAME MATCH_CRITERIA STATUS TEST_TYPE; do
        [[ -z ${event[$element]} ]] && missing+=($element)
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        error "'${event[FILENAME]}' is missing ${missing[@]}"
        flag_error=true
    fi

    if [[ -n ${event[TEST_TYPE]} && ! ${event[TEST_TYPE]} =~ ^(arithmetic|content|status)$ ]]; then
        error "'${event[FILENAME]}' does not contain a valid TEST_TYPE"
        flag_error=true
    fi

    if [[ ${event[TEST_TYPE]} =~ ^(arithmetic|status)$ ]]; then
        if [[ -n ${event[MATCH_CONTENT]} && ! ${event[MATCH_CONTENT]} =~ ^-?[0-9]+$ ]]; then
            error "'${event[FILENAME]}' MATCH_CONTENT must be an integer when performing arithmetic operations"
            flag_error=true
        fi
        if [[ -n ${event[MATCH_CRITERIA]} && ! ${event[MATCH_CRITERIA]} =~ ^(eq|ge|gt|le|lt|ne)$ ]]; then
            error "'${event[FILENAME]}' does not contain valid MATCH_CRITERIA for arithmetic operations"
            flag_error=true
        fi
    fi

    if [[ ${event[TEST_TYPE]} = content && -n ${event[MATCH_CRITERIA]} && ! ${event[MATCH_CRITERIA]} =~ ^(contains|does_not_contain|matches|does_not_match|null|not_null)$ ]]; then
        error "'${event[FILENAME]}' does not contain valid MATCH_CRITERIA for content operations"
        flag_error=true
    fi

    if [[ -n ${event[TRIGGER_CUSTOM]} && -n ${event[TRIGGER_NAMED]} ]]; then
        error "'${event[FILENAME]}' specifies both TRIGGER_CUSTOM and TRIGGER_NAMED (choose one or neither)"
        flag_error=true
    fi

    prepare_trigger

    if [[ $flag_error = true ]]; then
        return 1
    fi
}

warning(){
    echo "WARNING: $@" >&2
}


if (( $# == 0 )); then
    error "Please indicate target event files and/or directories"
    error "Try '${0##*/} --help' for more information."
    exit 1
elif (( $# == 1 )) && [[ $1 =~ ^(-h|--help)$ ]]; then
    echo "Usage: ${0##*/} <event files|folders>" >&2
    echo "Show notifications based on custom recurring events." >&2
    echo >&2
    echo "  --verify               verify event files without execution" >&2
    exit 0
fi

events=()
for arg in "${@}"; do
    if [[ $arg = --verify ]]; then
        option_verify=true
    elif [[ -f $arg ]]; then
        events+=("$arg")
    elif [[ -d $arg ]]; then
        if [[ -r $arg ]]; then
            while IFS= read -r line; do
                events+=("$line")
            done < <(find "$arg" -maxdepth 1 \( -empty -name '.*' -prune \) -o \( -name '*.conf' -o -name '*.txt' -print -type f -writable \))
        else
            error "Skipping '$arg' directory (no read access)"
        fi
    fi
done

if (( ${#events[@]} == 0 )); then
    error "You have not supplied any valid targets"
    exit 1
fi

for event_file in "${events[@]}"; do
    load_event

    if [[ $option_verify = true ]]; then
        verify_event
        continue
    elif [[ ${event[STATUS]} != enabled ]]; then
        continue
    fi

    verify_event || continue

    # execute event command
    event[command_output]=$(${event[COMMAND]} 2>/dev/null)
    event[exit]=$?

    # compare command output with match content (per match criteria)
    if [[ ${event[TEST_TYPE]} = arithmetic ]]; then
        if [[ ${event[command_output]} =~ ^-?[0-9]+$ ]]; then
            eval [[ ${event[command_output]} -${event[MATCH_CRITERIA]} ${event[MATCH_CONTENT]} ]] && event[triggered]=true
        fi
    elif [[ ${event[TEST_TYPE]} = content ]]; then
        if [[ ${event[MATCH_CRITERIA]} = contains ]]; then
            grep -q "${event[MATCH_CONTENT]}" <<< "${event[command_output]}" >/dev/null 2>&1
            if (( $? == 0 )); then
                event[triggered]=true
            elif (( $? > 1 )); then
                error "grep experienced an unknown error handling command output for '${event[FILENAME]}'"
            fi
        elif [[ ${event[MATCH_CRITERIA]} = does_not_contain ]]; then
            grep -q "${event[MATCH_CONTENT]}" <<< "${event[command_output]}" >/dev/null 2>&1
            if (( $? == 1 )); then
                event[triggered]=true
            elif (( $? > 1 )); then
                error "grep experienced an unknown error handling command output for '${event[FILENAME]}'"
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
        eval [[ ${event[exit]} -${event[MATCH_CRITERIA]} ${event[MATCH_CONTENT]} ]] && event[triggered]=true
    fi

    [[ ${event[triggered]} != true ]] && continue

    eval "${event[trigger]}" >/dev/null 2>&1

    if (( $? != 0 )) && [[ ${event[trigger_type]} != default ]]; then
        error "Trigger event for event file '${event[FILENAME]}' returned a nonzero exit code. Executing default trigger..."
        eval "$DEFAULT_TRIGGER" >/dev/null 2>&1
    fi

    if hash bash-config 2>/dev/null;
        bash-config "$event_file" STATUS triggered 2>/dev/null
    else
        sed -i 's/STATUS=enabled/STATUS=triggered/;s/STATUS = enabled/STATUS = triggered/' "$event_file"
    fi
    
    if (( $? != 0 )); then
        error "Problem updating the event file '${event[FILENAME]}' after trigger event"
    fi
done
