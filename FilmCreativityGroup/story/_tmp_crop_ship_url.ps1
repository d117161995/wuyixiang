$ErrorActionPreference = 'Stop'

$in  = 'C:\Users\wuyixiang\.cursor\projects\y-tmp-WuYiXiang-wuyixiang\assets\c__Users_wuyixiang_AppData_Roaming_Cursor_User_workspaceStorage_c2d1a3e2ab24dc40fdd64b0516f72487_images_00dab2ce3dba3262e968128f4ca9b866-016c77e6-b7ef-442b-88d9-a5bf361110ef.png'
$out1 = 'Y:\tmp\WuYiXiang\wuyixiang\story\_tmp_ship_text_zoom_a.png'
$out2 = 'Y:\tmp\WuYiXiang\wuyixiang\story\_tmp_ship_text_zoom_b.png'
$out3 = 'Y:\tmp\WuYiXiang\wuyixiang\story\_tmp_ship_text_zoom_c.png'

Add-Type -AssemblyName System.Drawing

$img = [System.Drawing.Image]::FromFile($in)
$bmp = New-Object System.Drawing.Bitmap $img

function Save-CropZoom([int]$x, [int]$y, [int]$w, [int]$h, [string]$outPath) {
    $cropRect = New-Object System.Drawing.Rectangle $x,$y,$w,$h
    $crop = New-Object System.Drawing.Bitmap $cropRect.Width, $cropRect.Height
    $g = [System.Drawing.Graphics]::FromImage($crop)
    $g.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g.DrawImage($bmp, 0, 0, $cropRect, [System.Drawing.GraphicsUnit]::Pixel)
    $g.Dispose()

    $zoom = New-Object System.Drawing.Bitmap ($cropRect.Width * 6), ($cropRect.Height * 6)
    $g2 = [System.Drawing.Graphics]::FromImage($zoom)
    $g2.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
    $g2.DrawImage($crop, 0, 0, $zoom.Width, $zoom.Height)
    $g2.Dispose()

    $zoom.Save($outPath, [System.Drawing.Imaging.ImageFormat]::Png)
    $crop.Dispose()
    $zoom.Dispose()
    Write-Output $outPath
}

# 多取几个区域覆盖“网址”所在位置（根据原图大致估计）
Save-CropZoom 140 335 520 220 $out1
Save-CropZoom 170 360 560 240 $out2
Save-CropZoom 210 380 620 260 $out3

$bmp.Dispose()
$img.Dispose()

