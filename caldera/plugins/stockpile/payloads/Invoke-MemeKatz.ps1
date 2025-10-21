add-type @"
using System;
using System.Runtime.InteropServices;
using Microsoft.Win32;
namespace Wallpaper {
 public enum Style: int {
  Tiled,
  Centered,
  Stretched,
  Fit
 }
 public class Setter {
  public
  const int SetDesktopWallpaper = 20;
  public
  const int UpdateIniFile = 0x01;
  public
  const int SendWinIniChange = 0x02;
  [DllImport("user32.dll", SetLastError = true, CharSet = CharSet.Auto)]
  private static extern int SystemParametersInfo(int uAction, int uParam, string lpvParam, int fuWinIni);
  public static void SetWallpaper(string path, Wallpaper.Style style) {
   SystemParametersInfo(SetDesktopWallpaper, 0, path, UpdateIniFile | SendWinIniChange);
  }
 }
}
"@
$imageURL = Invoke-RestMethod -Uri https://meme-api.herokuapp.com/gimme | Select-Object -Property url
$wallpaperPath = "$Env:UserProfile\\AppData\\Local\\wallpaper.jpg"
Invoke-WebRequest -Uri $imageURL.url -OutFile $wallpaperPath
[Wallpaper.Setter]::SetWallpaper((Convert-Path $wallpaperPath), "Fit")