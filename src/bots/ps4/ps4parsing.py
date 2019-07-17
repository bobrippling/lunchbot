from collections import defaultdict
import datetime
import re

from ps4config import default_max_players, PLAY_TIME

punctuation = [".", "?", ","]
time_prefixes = ["at"]
competitive_keywords = ["compet", "competitive", "1v1", "1v1me"]
parameter_re = re.compile('^([a-z]+)=(.*)')

def today_at(hour, min):
    return datetime.datetime.today().replace(
                    hour = hour,
                    minute = min,
                    second = 0,
                    microsecond = 0)

def date_with_year(year):
    return datetime.datetime(year, 1, 1)

def deserialise_time(s):
    parts = s.split(":")
    if len(parts) != 2:
        raise ValueError
    return today_at(int(parts[0]), int(parts[1]))

def parse_time(s, previous = None):
    allow_fractional_prefix = False
    am_pm = ""
    if len(s) >= 3 and s[-1] == "m" and (s[-2] == "a" or s[-2] == "p"):
        am_pm = s[-2]
        s = s[:-2]

    time_parts = s.split(":")
    if len(time_parts) > 2:
        raise ValueError

    if len(time_parts) == 1:
        time_parts = s.split(".")

    if len(time_parts) == 1:
        time_parts.append("00")

        # just a number by itself
        allow_fractional_prefix = True
    elif len(time_parts[1]) != 2:
        raise ValueError

    hour = int(time_parts[0])
    min = int(time_parts[1])

    if hour < 0 or min < 0:
        raise ValueError

    if len(am_pm):
        if hour > 12:
            raise ValueError
        if am_pm == "p":
            hour += 12
        # ignore allow_fractional_prefix, can't really say "half 2pm"
    else:
        # no am/pm specified, if it's before 8:00, assume they mean afternoon
        if hour < 8:
            hour += 12

        if allow_fractional_prefix:
            if previous == "half":
                min = 30

    return today_at(hour, min)

def maybe_parse_time(s, previous):
    try:
        return parse_time(s, previous)
    except ValueError:
        return None

def empty_parameters():
    return defaultdict(lambda: None)

def parse_stats_request(request):
    channel_name = None
    since = None
    parameters = empty_parameters()

    parts = request.split(" ")
    for part in parts:
        if not since and len(part) == 4:
            try:
                since = int(part)
                continue
            except ValueError:
                pass

        parameter_match = parameter_re.search(part)
        if parameter_match:
            try:
                parameters[parameter_match.group(1)] = int(parameter_match.group(2))
                continue
            except ValueError:
                return None

        if not channel_name:
            channel_name = part
            continue

        # unrecognised
        return None

    return channel_name, date_with_year(since) if since else None, parameters

def pretty_mode(mode):
    if mode == "compet":
        return "1v1"
    return mode

def parse_game_initiation(str, channel):
    parts = str.split(" ")

    when = None
    desc_parts = []
    player_count = default_max_players(channel)
    mode = None
    play_time = PLAY_TIME
    for i, part in enumerate(parts):
        while len(part) and part[-1] in punctuation:
            part = part[:-1]

        previous = parts[i - 1] if i > 0 else None

        maybe_when = maybe_parse_time(part, previous)
        if maybe_when:
            if when:
                return None

            when = maybe_when
            if len(desc_parts) and desc_parts[-1] in time_prefixes:
                desc_parts.pop()
            continue

        if part == "sextuple":
            player_count = 6
            continue
        if part in competitive_keywords:
            player_count = 2
            mode = "compet"
            play_time = 20
            continue

        desc_parts.append(part)

    if not when:
        return None

    return when, " ".join(desc_parts), player_count, play_time, mode
