# FFmpeg select filter command line parsing solutions

Your FFmpeg select filter expression is **syntactically correct**, but Windows command line parsing is breaking it at the comma, causing the "No such filter: '0)*lte(n'" error. The parser incorrectly interprets part of your mathematical expression as a filter name because the command line splits the argument before FFmpeg receives it.

## Immediate working solutions for your command

Your original attempt `ffmpeg -vf select=if(gte(n,0)*lte(n,310),1,eq(mod(n,2),0))` fails because Windows CMD treats unquoted commas as argument separators. Here are **three proven fixes** that will work immediately:

### Solution 1: Full double quotes (simplest)
```batch
ffmpeg -i input.mp4 -vf "select=if(gte(n,0)*lte(n,310),1,eq(mod(n,2),0))" output.mp4
```

### Solution 2: Using between() function (cleaner syntax)
```batch
ffmpeg -i input.mp4 -vf "select=if(between(n,0,310),1,eq(mod(n,2),0))" output.mp4
```

### Solution 3: Environment variable wrapper (most reliable)
```batch
set "FILTER=if(gte(n,0)*lte(n,310),1,eq(mod(n,2),0))"
ffmpeg -i input.mp4 -vf "select=%FILTER%" output.mp4
```

Each solution properly handles the motion-adaptive frame selection you're implementing: keeping all frames 0-310, then every other frame afterward. **Always include `setpts` filter** to fix timestamps after frame selection:
```batch
ffmpeg -i input.mp4 -vf "select=if(between(n,0,310),1,eq(mod(n,2),0)),setpts=N/FRAME_RATE/TB" output.mp4
```

## Why the parsing error occurs on Windows

Windows command processors interpret your expression differently than Unix shells. The specific breaking point at "0)*lte(n" reveals that **CMD splits the argument at the first unprotected comma**, treating everything after as separate arguments. FFmpeg then receives a malformed filter graph where `0)*lte(n` appears to be a filter name.

The three-level escaping challenge compounds this issue. FFmpeg requires escaping at the filter option level (for colons and backslashes), the filtergraph level (for brackets, semicolons, commas), and the shell level (Windows-specific rules for parentheses, spaces, and special characters). Your unquoted expression fails at the shell level before FFmpeg even processes it.

## Platform-specific escaping strategies

### Windows CMD escaping options
For CMD, you have multiple escaping methods beyond basic quoting. **Caret escaping** works for individual special characters:
```batch
ffmpeg -i input.mp4 -vf select=if^(between^(n,0,310^),1,eq^(mod^(n,2^),0^)^) output.mp4
```

However, this approach becomes unwieldy for complex expressions. **Batch files with delayed expansion** provide better reliability:
```batch
@echo off
setlocal enabledelayedexpansion
set "COMPLEX_FILTER=select=if(between(n,0,310),1,eq(mod(n,2),0))"
ffmpeg -i "%~1" -vf "!COMPLEX_FILTER!" "%~dpn1_filtered%~x1"
```

### PowerShell advantages
PowerShell handles complex expressions more gracefully using single quotes to prevent variable expansion:
```powershell
ffmpeg -i input.mp4 -vf 'select=if(between(n,0,310),1,eq(mod(n,2),0))' output.mp4
```

You can also use **here-strings** for multi-line filter definitions:
```powershell
$filter = @'
select=if(between(n,0,310),1,eq(mod(n,2),0)),setpts=N/FRAME_RATE/TB
'@
ffmpeg -i input.mp4 -vf $filter output.mp4
```

## Alternative approaches for motion-adaptive frame thinning

### Using mpdecimate for automatic motion detection
The `mpdecimate` filter removes near-duplicate frames based on motion analysis, providing true motion-adaptive processing without manual frame number ranges:
```batch
ffmpeg -i input.mp4 -vf "mpdecimate=hi=6400:lo=1200:frac=0.33,fps=30,setpts=N/FRAME_RATE/TB" output.mp4
```

Parameters control sensitivity: **hi** sets the threshold for 8x8 block differences, **lo** for larger area changes, and **frac** determines what fraction of the frame must change to keep it.

### Motion-compensated interpolation with minterpolate
For smoother 60fps to 30fps conversion with intelligent frame selection:
```batch
ffmpeg -i input.mp4 -vf "minterpolate=fps=30:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:scd=none" output.mp4
```

This approach uses motion vectors to select optimal frames rather than fixed patterns, often producing superior results for actual motion-adaptive thinning.

### Filter script files for complex logic
Create a text file `complex_select.txt` containing your filter:
```
[0:v]select='if(between(n,0,310),1,eq(mod(n,2),0))',setpts=N/FRAME_RATE/TB[v]
```

Apply with:
```batch
ffmpeg -i input.mp4 -filter_script complex_select.txt -map "[v]" output.mp4
```

This completely avoids command line parsing issues by reading the filter from a file.

## Multi-pass processing for complex patterns

When single-command solutions become too complex, split the task into manageable passes:

```batch
rem Pass 1: Extract frames 0-310
ffmpeg -i input.mp4 -vf "select=between(n,0,310),setpts=N/FRAME_RATE/TB" part1.mp4

rem Pass 2: Extract every other frame from 311 onward
ffmpeg -i input.mp4 -vf "select=gte(n,311)*not(mod(n,2)),setpts=N/FRAME_RATE/TB" part2.mp4

rem Concatenate results
echo file 'part1.mp4' > concat.txt
echo file 'part2.mp4' >> concat.txt
ffmpeg -f concat -safe 0 -i concat.txt -c copy final_output.mp4
```

## Best practices for FFmpeg on Windows

Always follow these guidelines to avoid parsing issues:

1. **Quote entire filter expressions** with double quotes
2. **Use between() instead of gte()*lte()** for range checks
3. **Test incrementally** with simpler expressions before adding complexity
4. **Include setpts=N/FRAME_RATE/TB** after any frame selection to fix timestamps
5. **Consider PowerShell over CMD** for complex automation
6. **Use filter script files** for expressions exceeding command line limits
7. **Verify with -v verbose** flag to see detailed parsing information

For debugging, add the `showinfo` filter to verify which frames are selected:
```batch
ffmpeg -i input.mp4 -vf "select=if(between(n,0,310),1,eq(mod(n,2),0)),showinfo" -f null -
```

## Conclusion

Your ATFI motion-adaptive frame selection concept is sound, but Windows command line parsing requires proper quoting or alternative syntax. The **simplest immediate fix** is wrapping your entire filter in double quotes. For production use, consider the **between() function** for cleaner syntax or **mpdecimate** for true motion-based frame selection. The motion-compensated interpolation approach with `minterpolate` often produces the best visual results for 60fps to 30fps conversion, automatically handling both motion and static scenes intelligently without manual frame number specifications.