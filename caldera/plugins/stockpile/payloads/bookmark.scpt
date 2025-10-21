property theTitle : "Important docs"
property bookmarkFolder : "Bookmarks Bar"

on run argv
    tell application "Google Chrome"
      try
          tell active tab of window 1
              repeat while loading is true
                  delay 0.3
              end repeat
          end tell
      end try
      log "Setting new bookmark: " & item 1 of argv & ""
      tell its bookmark folder bookmarkFolder
          set theResult to make new bookmark item with properties {URL:"" & item 2 of argv & ""}
          set title of theResult to "" & item 1 of argv & ""
      end tell
    end tell
end run