# Prefix

Keyboard shortcuts after prefix key.

| Key   | Description                 |
| ----- | --------------------------- |
| `Tab` | Select last selected window |
| `C-l` | Toggle terminal logging     |
|       |                             |
|       |                             |
|       |                             |
|       |                             |
|       |                             |
|       |                             |
|       |                             |
|       |                             |
|       |                             |
|       |                             |
|       |                             |
|       |                             |
|       |                             |



# copy-mode-vi

Keyboard shortcuts for Copy mode.

## Movement

| Key                 | Description                              |
| ------------------- | ---------------------------------------- |
| `j` or `Down`       | Move cursor down                         |
| `k` or `Up`         | Move cursor up                           |
| `h` or `Left`       | Move cursor left                         |
| `l` or `Right`      | Move cursor right                        |
| `C-b` or `PageUp`   | Scroll page up                           |
| `C-f` or `PageDown` | Scroll page down                         |
| `C-k`               | Scroll half page up                      |
| `C-j`               | Scroll half page down                    |
| `M-k` or `C-Up`     | Scroll one line up                       |
| `M-j` or `C-Down`   | Scroll one line down                     |
| `g`                 | Go to the top of the terminal history    |
| `G`                 | Go to the bottom of the terminal history |

## Selection and copy

| Key                 | Description                                                  |
| ------------------- | ------------------------------------------------------------ |
| `Space` or `v`      | Start selection                                              |
| `V`                 | Select line                                                  |
| `C-v`               | Toggle block selection                                       |
| `Esc`               | Clear and stop selection                                     |
| `Enter` or `y`      | Copy selection and exit copy mode                            |
| `D`                 | Copy till end of the line and exit copy mode                 |
| `Y`                 | Copy whole line and exit copy mode                           |

## Search

| Key                 | Description                                                  |
| ------------------- | ------------------------------------------------------------ |
| `#`                 | Search for word under a cursor backwards                     |
| `*`                 | Search for word under a cursor forward                       |
| `/`                 | Search entered text forward                                  |
| `?`                 | Search entered text backwards                                |
| `n`                 | Repeat search (find next)                                    |
| `N`                 | Repeat search in reverse (find previous)                     |

## Cursor position

| Key  | Description                                                  |
| ---- | ------------------------------------------------------------ |
| `0`  | Put cursor at the start of the line                          |
| `^`  | Put cursor on the first non whitespace character on the line |
| `$`  | Put cursor at the end of the line                            |
| `w`  | Put cursor at the beginning of the next word                 |
| `b`  | Put cursor at the beginning of the current or previous word  |
| `e`  | Put cursor at the end of the current or next word            |
| `W`  | Put cursor after next space                                  |
| `B`  | Put cursor before previous space                             |
| `E`  | Put cursor before next space                                 |
| `H`  | Put cursor at the top of current screen                      |
| `L`  | Put cursor at the bottom of current screen                   |
| `M`  | Put cursor at the middle of current screen                   |
| `%`  | Put cursor at next `{}` or `[]` or `()` matching bracket     |
| `{`  | Put cursor at the blank line before previous paragraph       |
| `}`  | Put cursor at the blank line after current or next paragraph |

### Jumping

| Key  | Description                                         |
| ---- | --------------------------------------------------- |
| `f`  | Put cursor (jump) forward to entered character      |
| `F`  | Put cursor (jump) backwards to entered character    |
| `t`  | Put cursor (jump) forward before entered character  |
| `T`  | Put cursor (jump) backwards after entered character |
| `;`  | Repeat jump                                         |
| `,`  | Repeat jump in reverse                              |

## Mouse

| Key                  | Description              |
| -------------------- | ------------------------ |
| `Left click`         | Clear and stop selection |
| `Right click`        | Exit copy mode and paste |
| `Left hold and drag` | Select and copy          |
| `Scroll`             | Move 5 lines up or down  |
| `Double left click`  | Select word and copy     |
| `Triple left click`  | Select line and copy     |

## Miscellaneous

| Key          | Description                                                  |
| ------------ | ------------------------------------------------------------ |
| `1-9`        | Repeat key 1-9 times<br/>e.g: `3` and then `K` will scroll 3 lines up. |
| `:`          | Go to line number, count from the bottom                     |
| `C-c` or `q` | Exit copy mode                                               |
