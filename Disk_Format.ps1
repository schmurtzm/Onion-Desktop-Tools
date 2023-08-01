param (
    [string]$Drive_Number
)
if (-not $Drive_Number) {
    Write-Host "This script requires a drive number argument."
    Write-Host "Usage: $ScriptName -Drive_Number <drive_number>"
    exit 1
}

$ScriptPath = $MyInvocation.MyCommand.Path
$ScriptDirectory = Split-Path $ScriptPath -Parent
Set-Location -Path $ScriptDirectory
[Environment]::CurrentDirectory = Get-Location


#$Drive_Number = 6

Write-Host "Drive Number in script arg: $Drive_Number"


function GetLetterFromDriveNumber {
    $commandOutput = & "tools\RMPARTUSB.exe" "drive=$Drive_Number" "GETDRV"
    $driveLetterPattern = 'SET USBDRIVELETTER=(.+)'
    $driveLetterMatch = $commandOutput | Select-String -Pattern $driveLetterPattern
     Write-Host "driveLetterMatch1: $driveLetterMatch"
    if ($driveLetterMatch) {
        $driveLetter = $driveLetterMatch.Matches.Groups[1].Value
        Write-Host "Drive Letter: $driveLetter"
        return $driveLetter  # Retourner la valeur de $driveLetter
    }
    else {
        Write-Host "Drive Letter not found"
        return $null  # Retourner $null si la lettre de lecteur n'est pas trouv�e
    }
}



$driveLetter = GetLetterFromDriveNumber

# if the drive ha already a letter affected :
Write-Host "driveLetterMatch2: $driveLetterMatch"
if ($driveLetter -ne $null) {

    # if some files are already here, we alert the user that all is going to be erased.
    $items = Get-ChildItem -Path "$($driveLetter)\"

    # Vérifier si la carte SD est vierge
    if ($items.Count -eq 0) {
        #################### empty partition ####################
        Write-Host "Blank SD card."
        $messageBoxText = "It seems that your SD card is empty so no backup required.`n" + 
        "Continue ?`n`n"
    }
    else {
        Write-Host "The SD card contains files/folders."
        Write-Host "Looking for a previous Onion installation in ${driveLetter}\.tmp_update\onionVersion\version.txt"
        $verionfilePath = "${driveLetter}\.tmp_update\onionVersion\version.txt"
        if (Test-Path -Path $verionfilePath -PathType Leaf) {
            #################### previous Onion ####################
            $content = Get-Content -Path $verionfilePath -Raw
            Write-Host "Onion version $content already installed on this SD card."
            $messageBoxText = "Onion $content is installed on this SD card.`n" +
            "Are you sure that you want to format the SD card?`n`n" +
            "(Saves, roms, configuration: everything will be lost!)"
        }
        elseif ((Test-Path -Path "${Target}\.tmp_update") -and (Test-Path -Path "${Target}\miyoo\app\.tmp_update\onion.pak")) {
            #################### Fresh Onion install files (not executed on MM) ####################
            Write-Host "It seems to be and non installed Onion version"
            $label_right.Text += "`r`nFresh Onion install files on ${Target}"
            Write-Host "It seems to be and non installed Onion version."
            $messageBoxText = "It seems to be and non installed Onion version.`n" +
            "Are you sure that you want to format the SD card?`n`n" +
            "(Saves, roms, configuration: everything will be lost!)"
        }
        elseif (Test-Path -Path "${driveLetter}\RApp\") {
            #################### previous Stock ####################
            Write-Host "It seems to be a stock SD card from Miyoo"
            $messageBoxText = "It seems to be a stock SD card from Miyoo.`n" +
            "Are you sure that you want to format the SD card?`n`n" +
            "(Saves, roms, configuration: everything will be lost!)`n`n" +
            "Note that it's not recommended to install Onion on the `n" +
            "stock SD card (as the quality is not good you could have`n" +
            "data corruption which may prevent Onion from working properly)."

        }
        else {
            #################### unknown files ####################
            Write-Host "Not Onion or Stock"
            $messageBoxText = "It seems that your SD card contains some files.`n" +
            "Are you sure that you want to format the SD card?`n`n" +
            "(Everything on the SD card will be lost!)"
        }
    }
}
else {
    #################### No partition ####################
    Write-Host "No partition recognized by Windows : SD card not formated or unknown partition type."
    $messageBoxText = "It seems that your SD card is not formated`n" + 
    "(or contains an unknown partition type as EXT/linux).`n" +
    "Are you sure that you want to format the SD card?`n`n" +
    "(Everything on the SD card will be lost!)"
}

$messageBoxCaption = "Formating Confirmation"
$messageBoxButtons = [System.Windows.Forms.MessageBoxButtons]::YesNo
$messageBoxIcon = [System.Windows.Forms.MessageBoxIcon]::Warning
$result = [System.Windows.Forms.MessageBox]::Show($messageBoxText, $messageBoxCaption, $messageBoxButtons, $messageBoxIcon)

if ($result -eq [System.Windows.Forms.DialogResult]::No) {
    exit 1  # Exit script with error code 1
}


Write-Host "Unlocking drive in case of some apps hooks the drive."
.\tools\LockHunter\LockHunter32.exe /unlock $driveLetter /kill /silent

# formating (SURE option arg is not implemented -> some popups but gives some additional information during formating) 
Write-Host "Start formating ..."


& .\tools\RMPARTUSB-old.exe drive=$Drive_Number WINPE FAT32 NOACT  VOLUME=Onion
#.\tools\RMPARTUSB-old.exe drive=$Drive_Number WINPE FAT32 NOACT USBFDD VOLUME=Onion
# Check the exit code
if ($LASTEXITCODE -ne 0) {
    Write-Host "An error occurred while executing RMPARTUSB-old.exe."
    exit 2  # Exit the script with error code 2
} else {
    Write-Host "Format command executed successfully."
    # Continue with other actions as needed.
}

sleep 5
$driveLetter = GetLetterFromDriveNumber


