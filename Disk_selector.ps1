param (
    [string]$Title
)

Write-Host "Title: $Title"
$ScriptPath = $MyInvocation.MyCommand.Path
$ScriptDirectory = Split-Path $ScriptPath -Parent
Set-Location -Path $ScriptDirectory
Add-Type -AssemblyName System.Windows.Forms



$form = New-Object System.Windows.Forms.Form
if ($Title) { $Title = "- $Title"}
$form.Text = "Drive Selector $Title"
$form.Size = New-Object System.Drawing.Size(430, 300)
$form.StartPosition = "CenterScreen"
$iconPath = Join-Path -Path $PSScriptRoot -ChildPath "tools\res\sdcard.ico"
$icon = New-Object System.Drawing.Icon($iconPath)
$form.Icon = $icon

$driveRadioButtons = New-Object System.Collections.ArrayList
$selectedDrive = ""

$gb = New-Object System.Windows.Forms.GroupBox
$form.Controls.Add($gb)
$gb.Width = 390
$gb.Left = 10


function ShowNoDriveFoundLabel {
    $noDriveLabel = New-Object System.Windows.Forms.Label
    $noDriveLabel.Text = "No drive found.`nCheck that your SD card is inserted in your SD card reader`nand that Onion Desktop Tools is running as administrator."
    $noDriveLabel.Location = New-Object System.Drawing.Point(20, 20)
    $noDriveLabel.AutoSize = $true
    $gb.Controls.Add($noDriveLabel)
}
function RefreshDriveList {
    $gb.Controls.Clear()
    $driveRadioButtons.Clear()
    $button_ok.Enabled = $false
    $refreshButton.Text = "Loading..."
    $form.Refresh()
    $commandOutput = & "tools\RMPARTUSB.exe" "LIST"

    $lines = $commandOutput -split '\r?\n'  # Split the command result into an array of lines
    $locationY = 20
    foreach ($drive in $lines) {
        # if ($drive -match '\*?DRIVE (\d+) -\s+([\d.]+[KMGTP]?iB)\s+(.*?)\s+Fw=(\w+)\s+Sno=(\w+)\s+(\w+):') {
    
        if ($drive -match '\*?DRIVE (\d+) -\s+([\d.]+[KMGTP]?iB)\s+(.*?)\s+Fw=(\w+)*\s+Sno=(\w+)*\s+(\w+):') {
            $driveNumber = $Matches[1]
            $driveSize = $Matches[2]
            $driveDescription = $Matches[3].Trim()
            $firmware = $Matches[4]
            $serialNumber = $Matches[5]
            $driveLetter = $Matches[6]

            Write-Host "Drive Number: $driveNumber"
            Write-Host "Drive Size: $driveSize"
            Write-Host "Drive Description: $driveDescription"
            Write-Host "Firmware: $firmware"
            Write-Host "Serial Number: $serialNumber"
            Write-Host "Drive Letter: $driveLetter"
    
            Write-Host "--------------------------"

            $driveRadioButton = New-Object System.Windows.Forms.RadioButton
            $driveRadioButton.Text = "${driveLetter}: - Drive${driveNumber} - ${driveDescription} (${driveSize})"
            $driveRadioButton.Location = New-Object System.Drawing.Point(20, $locationY)
            $driveRadioButton.AutoSize = $false
            $driveRadioButton.Width = 360
            $driveRadioButton.Tag = "${driveNumber},${driveLetter}"

            $locationY += 30
            [void]$driveRadioButtons.Add($driveRadioButton)
            $gb.Controls.Add($driveRadioButton)

            $driveRadioButton.Add_Click({
                    $button_ok.Enabled = $true
                })
        }
    }

    if ($driveRadioButtons.Count -eq 0) {
        ShowNoDriveFoundLabel
        $locationY = 50
    }

    $gb.Height = $locationY + 20
    $refreshButton.Top = $gb.Bottom + 20
    $button_ok.Top = $gb.Bottom + 20
    $button_cancel.Top = $gb.Bottom + 20
    $refreshButton.Text = "Refresh"

    $form.Refresh()
}

$refreshButton = New-Object System.Windows.Forms.Button
$refreshButton.Text = "Refresh"
$refreshButton.Location = [System.Drawing.Point]::new(20, $gb.Bottom + 20)
$form.Controls.Add($refreshButton)
$refreshButton.Add_Click({
        RefreshDriveList
    })

$button_cancel = New-Object System.Windows.Forms.Button
$button_cancel.Text = "Cancel"
$button_cancel.Location = [System.Drawing.Point]::new($refreshButton.Right + 20, $refreshButton.Top)
$form.CancelButton = $button_cancel
$form.Controls.Add($button_cancel)

$button_ok = New-Object System.Windows.Forms.Button
$button_ok.Text = "OK"
$button_ok.Location = [System.Drawing.Point]::new($button_cancel.Right + 20, $refreshButton.Top)
$button_ok.DialogResult = [System.Windows.Forms.DialogResult]::OK
$button_ok.Enabled = $false
$button_ok.Add_Click({
        $selectedDrive = $gb.Controls | Where-Object { $_.Checked } | Select-Object -ExpandProperty Tag
        $button_ok.Enabled = $false
    })
$form.AcceptButton = $button_ok
$form.Controls.Add($button_ok)




RefreshDriveList

[void]$form.ShowDialog()

if ([System.Windows.Forms.DialogResult]::OK -eq $form.DialogResult) {
    $selectedTag = $gb.Controls | Where-Object { $_.Checked } | Select-Object -ExpandProperty Tag
    $selectedTagSplitted = $selectedTag.Split(",")
    $Drive_Number = $($selectedTagSplitted[0])
    $Drive_Letter = $($selectedTagSplitted[1])
    Write-Host "Disk Number: $Drive_Number"
    Write-Host "Disk Letter: $Drive_Letter"
}

if ([System.Windows.Forms.DialogResult]::CANCEL -eq $form.DialogResult) {
    Write-Host "Canceled"
    $Drive_Number = ""
    $Drive_Letter = ""
}