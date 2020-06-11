#!/usr/bin/expect

# This script is from http://www.afterstep.org/keyboard.html, original is here
# http://www.ibb.net/~anne/keyboard/keyboard.html, but it didn't work when I wrote this.
# Also info taken from here https://unix.stackexchange.com/a/13444.
# It's used for fixing Backspace and Delete keys on some devices that uses VT100 terminal scheme.

eval spawn -noecho $argv

# Change ^? to ^H
# Change ^[[3~ to ^D
interact {
 \177        {send "\010"}
 "\033\[3~"  {send "\004"}
}
