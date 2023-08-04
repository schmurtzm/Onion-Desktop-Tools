# Onion-Desktop-Tools-v0.0.8

param (
    [Parameter(Mandatory = $false)]
    [string]$HighDPI
)
$selectedTag = ""
$ScriptPath = $MyInvocation.MyCommand.Path
$ScriptDirectory = Split-Path $ScriptPath -Parent
Set-Location -Path $ScriptDirectory
[Environment]::CurrentDirectory = Get-Location

if (-Not (Test-Path "downloads" -PathType Container)) {
    New-Item -ItemType Directory -Path "downloads"
}
if (-Not (Test-Path "backups" -PathType Container)) {
    New-Item -ItemType Directory -Path "backups"
}

Remove-Item -Path ODT_update_temporary.ps1 -ErrorAction SilentlyContinue

# Read the Menu.ps1 file and get the version number from the first line
$menuContent = Get-Content -Path $MyInvocation.MyCommand.Path
if ($menuContent -and $menuContent[0]) {
    $currentVersion = $menuContent[0] -replace "# Onion-Desktop-Tools-"
    Write-Host "ODT version : $currentVersion"
}
else {
    Write-Host "Failed to retrieve the current version from Menu.ps1 file."
    return
}

Add-Type -AssemblyName System.Windows.Forms

#$HighDPI = 1
if ($HighDPI -eq 1) {
    # Scaling
    ##################################################
    # $DPISetting = (Get-ItemProperty 'HKCU:\Control Panel\Desktop\WindowMetrics' -Name AppliedDPI).AppliedDPI
    # $dpiKoef = $DPISetting / 96
    # [System.Windows.Forms.Application]::EnableVisualStyles();
    
    Add-Type -TypeDefinition '
    public class DPIAware {
        [System.Runtime.InteropServices.DllImport("user32.dll")]
        public static extern bool SetProcessDPIAware();
    }
    '
    [System.Windows.Forms.Application]::EnableVisualStyles()
    [void] [DPIAware]::SetProcessDPIAware() 
}

# Create environment


# Create main window
$Form = New-Object System.Windows.Forms.Form
$Form.Text = "Onion Desktop Tools"
$Form.Size = New-Object System.Drawing.Size(505, 320)
$form.StartPosition = "CenterScreen"
$iconPath = Join-Path -Path $PSScriptRoot -ChildPath "tools\res\onion.ico"
$icon = New-Object System.Drawing.Icon($iconPath)
$form.Icon = $icon

$Form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedSingle
$Form.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen

# Create TabControl control
$TabControl = New-Object System.Windows.Forms.TabControl
$TabControl.Dock = [System.Windows.Forms.DockStyle]::Fill
# Add the TabControl event handler

# Event handler for TabControl SelectedIndexChanged event
$TabControl_SelectedIndexChanged = {
    if ($TabControl.SelectedTab -eq $AboutTab) {
        $OKButton.Visible = $false
    }
    else {
        $OKButton.Visible = $true
    }
}
$TabControl.add_SelectedIndexChanged($TabControl_SelectedIndexChanged)


# Function to get the selected option from the current tab
function GetSelectedOption {
    $currentTab = $TabControl.SelectedTab

    foreach ($control in $currentTab.Controls) {
        if ($control.GetType().Name -eq "GroupBox") {
            foreach ($radioButton in $control.Controls) {
                if ($radioButton.Checked) {
                    return $radioButton
                }
            }
        }
    }

    return $null
}

# Add Click event for the "OK" button
$OKButton_Click = {
    $selectedOption = GetSelectedOption

    if ($selectedOption -ne $null) {
        Write-Host "Selected option in '$($TabControl.SelectedTab.Text)': $selectedOption.text"
        Write-Host "$PSScriptRoot"
        #$scriptPath = Join-Path $PSScriptRoot "downloadupdate.ps1"

        if ($TabControl.SelectedTab -eq $OnionConfigTab) {
            # Special case for Onion Configuration tab (we run the script contained in the tag of the radio button)
            $OKButton.Enabled = 0
            & $selectedOption.Tag
            $OKButton.Enabled = 1
        }

        if ($selectedOption.text -eq $InstallUpdateRadioButton0.Text) {
            # Install / Upgrade / Reinstall Onion without formatting SD card
            $OKButton.Enabled = 0
            $CurrentDrive = Get_Drive "Select target drive for Onion"
            if ($CurrentDrive -ne $null) {
                Write-Host "{$CurrentDrive[1]}:"
                . "$PSScriptRoot\Onion_Install_Download.ps1"
                . "$PSScriptRoot\Onion_Install_Extract.ps1" -Target "$($CurrentDrive[1]):"
            }
            $OKButton.Enabled = 1
        }
        
        if ($selectedOption.text -eq $InstallUpdateRadioButton1.Text) {
            # "Format SD card or install Onion"
            $OKButton.Enabled = 0
            $CurrentDrive = Get_Drive "Select target drive for Onion"
            if ($CurrentDrive -ne $null) {
                # Sometimes a checkdisk is required to format 
                # $wgetProcess = Start-Process -FilePath "cmd" -ArgumentList "/k chkdsk $($CurrentDrive[1]): /F /X & echo.&echo Close this window to continue"  -PassThru
                # $wgetProcess.WaitForExit()
                . "$PSScriptRoot\Disk_Format.ps1" -Drive_Number $CurrentDrive[0]
                if ($?) {
                    . "$PSScriptRoot\Onion_Install_Download.ps1"
                    . "$PSScriptRoot\Onion_Install_Extract.ps1" -Target "$($CurrentDrive[1]):"
                }
                else {
                    Write-Host "Operation canceled or something wrong during formating" 
                }
            }
            $OKButton.Enabled = 1
        }

        if ($selectedOption.text -eq $InstallUpdateRadioButton2.Text) {
            # "Migrate stock SD card to a new SD card with Onion"
            $OKButton.Enabled = 0
            $messageBoxText = "Insert Miyoo Stock SD card now."
            $messageBoxCaption = "Stock Backup"
            $messageBoxButtons = [System.Windows.Forms.MessageBoxButtons]::OK
            $messageBoxIcon = [System.Windows.Forms.MessageBoxIcon]::Information
            [System.Windows.Forms.MessageBox]::Show($messageBoxText, $messageBoxCaption, $messageBoxButtons, $messageBoxIcon)
            $CurrentDrive = Get_Drive "Select stock SD card"
            if ($CurrentDrive -ne $null) {
                . "$PSScriptRoot\Onion_Save_Backup.ps1" -Drive_Number $CurrentDrive[0]
                
                $messageBoxText = "Insert Onion target SD card now."
                $messageBoxCaption = "Backup restoration"
                $messageBoxButtons = [System.Windows.Forms.MessageBoxButtons]::OK
                $messageBoxIcon = [System.Windows.Forms.MessageBoxIcon]::Information
                [System.Windows.Forms.MessageBox]::Show($messageBoxText, $messageBoxCaption, $messageBoxButtons, $messageBoxIcon)
                $CurrentDrive = Get_Drive "Select target drive for Onion"
                if ($CurrentDrive -ne $null) {
                    # Sometimes a chkdsk is required to format 
                    # $wgetProcess = Start-Process -FilePath "cmd" -ArgumentList "/k chkdsk $($CurrentDrive[1]): /F /X & echo.&echo Close this window to continue"  -PassThru
                    # $wgetProcess.WaitForExit()
                    . "$PSScriptRoot\Disk_Format.ps1" -Drive_Number $CurrentDrive[0]
                    if ($?) {
                        . "$PSScriptRoot\Onion_Install_Download.ps1"
                        . "$PSScriptRoot\Onion_Install_Extract.ps1" -Target "$($CurrentDrive[1]):"
                        . "$PSScriptRoot\Onion_Save_Restore.ps1" -Target "$($CurrentDrive[1]):"
                    }
                }
            }
            $OKButton.Enabled = 1
        }
        if ($selectedOption.text -eq $OtherToolsRadioButton3.text) {   #Check for errors (chkdsk)
            $OKButton.Enabled = 0
            $CurrentDrive = Get_Drive "Select a drive to check"
            if ($CurrentDrive -ne $null) {
                $wgetProcess = Start-Process -FilePath "cmd" -ArgumentList "/k chkdsk $($CurrentDrive[1]): /F /X & echo.&echo Close this window to continue"  -PassThru
                $wgetProcess.WaitForExit()
            }
            $OKButton.Enabled = 1
        }

        if ($selectedOption.text -eq "Format SD card in FAT32") {
            $OKButton.Enabled = 0
            $CurrentDrive = Get_Drive "Select a drive to format"
            if ($CurrentDrive -ne $null) {
                . "$PSScriptRoot\Disk_Format.ps1" -Drive_Number $CurrentDrive[0]
            }
            $OKButton.Enabled = 1
        }

        if ($selectedOption.text -eq $BackupRestoreRadioButton1.Text) {
            $OKButton.Enabled = 0
            $CurrentDrive = Get_Drive "Select a drive to backup"
            if ($CurrentDrive -ne $null) {
                . "$PSScriptRoot\Onion_Save_Backup.ps1" $CurrentDrive[1]
            }
            $OKButton.Enabled = 1
        }

        if ($selectedOption.text -eq $BackupRestoreRadioButton2.Text) {
            $OKButton.Enabled = 0
            $CurrentDrive = Get_Drive "Select a destination drive"
            if ($CurrentDrive -ne $null) {
                . "$PSScriptRoot\Onion_Save_Restore.ps1" -Target "$($CurrentDrive[1]):"
            }
            $OKButton.Enabled = 1
        }
             
    }
}

function Get_Drive($Title) {
    # Call Disk_selector.ps1 to get selectedTag
    . "$PSScriptRoot\Disk_selector.ps1" -Title $Title

    # Check if selectedTag is not empty
    if ($selectedTag -ne "") {
        $selectedTagSplitted = $selectedTag.Split(",")
        $Drive_Number = $selectedTagSplitted[0]
        $Drive_Letter = $selectedTagSplitted[1]
        Write-Host "Disk Number: $Drive_Number"
        Write-Host "Disk Letter: $Drive_Letter"
        Write-Host "Selected Tag: $selectedTag"
        return , $Drive_Number, $Drive_Letter
    }
    else {
        return $null
    }
}

# Tab "Install or Update Onion"
$InstallUpdateTab = New-Object System.Windows.Forms.TabPage
$InstallUpdateTab.Text = "Install or Update Onion"
$TabControl.TabPages.Add($InstallUpdateTab)

# Create GroupBox control for the "Install and Update Onion" tab
$InstallUpdateGroupBox = New-Object System.Windows.Forms.GroupBox
$InstallUpdateGroupBox.Location = New-Object System.Drawing.Point(20, 20)
$InstallUpdateGroupBox.Size = New-Object System.Drawing.Size(440, 200)
$InstallUpdateTab.Controls.Add($InstallUpdateGroupBox)

# Add radio buttons to the GroupBox
$InstallUpdateRadioButton0 = New-Object System.Windows.Forms.RadioButton
$InstallUpdateRadioButton0.Location = New-Object System.Drawing.Point(20, 30)
$InstallUpdateRadioButton0.Size = New-Object System.Drawing.Size(380, 20)
$InstallUpdateRadioButton0.Text = "Install / Upgrade / Reinstall Onion (without formatting SD card)"
$InstallUpdateGroupBox.Controls.Add($InstallUpdateRadioButton0)
$tooltip = New-Object System.Windows.Forms.ToolTip
$tooltip.SetToolTip($InstallUpdateRadioButton0, "This will download and update Onion. It will keep your data`n(including ROMs, saves, and RetroArch configuration)")

# Add radio buttons to the GroupBox
$InstallUpdateRadioButton1 = New-Object System.Windows.Forms.RadioButton
$InstallUpdateRadioButton1.Location = New-Object System.Drawing.Point(20, 60)
$InstallUpdateRadioButton1.Size = New-Object System.Drawing.Size(380, 20)
$InstallUpdateRadioButton1.Text = "Format SD card and install Onion"
$InstallUpdateGroupBox.Controls.Add($InstallUpdateRadioButton1)
$tooltip = New-Object System.Windows.Forms.ToolTip
$tooltip.SetToolTip($InstallUpdateRadioButton1, "This will format your SD card in FAT32`n(all the data on the SD card will be deleted),`nThen it will download and install Onion on your SD Card.")

$InstallUpdateRadioButton2 = New-Object System.Windows.Forms.RadioButton
$InstallUpdateRadioButton2.Location = New-Object System.Drawing.Point(20, 90)
$InstallUpdateRadioButton2.Size = New-Object System.Drawing.Size(380, 20)
$InstallUpdateRadioButton2.Text = "Migrate stock SD card to a new SD card with Onion"
$InstallUpdateGroupBox.Controls.Add($InstallUpdateRadioButton2)
$tooltip.SetToolTip($InstallUpdateRadioButton2, "This is a complete migration procedure for Onion.`nIt will backup your Miyoo stock SD card (bios, ROMs, and saves)`nthen it will format your new SD card in FAT32, download and`ninstall Onion, and then restore your stock backup data.")

# Tab "Onion configuration"
$OnionConfigTab = New-Object System.Windows.Forms.TabPage
$OnionConfigTab.Text = "Onion configuration"
$TabControl.TabPages.Add($OnionConfigTab)

# Create GroupBox control for the "Onion configuration" tab
$OnionConfigGroupBox = New-Object System.Windows.Forms.GroupBox
$OnionConfigGroupBox.Location = New-Object System.Drawing.Point(20, 20)
$OnionConfigGroupBox.Size = New-Object System.Drawing.Size(440, 200)
$OnionConfigTab.Controls.Add($OnionConfigGroupBox)

# Retrieve Onion configuration files
$onionConfigFiles = Get-ChildItem -Path $PSScriptRoot -Filter "Onion_Config_*.ps1"

# Initial position of radio buttons
$radioButtonLeft = 20
$radioButtonTop = 30
$radioButtonMargin = 10

# Create radio buttons for each Onion configuration file
Write-Host "Adding Onion configuration scripts : "
foreach ($configFile in $onionConfigFiles) {
    # Read the first line as a comment to get the radio button name
    $radioButtonText = Get-Content -Path $configFile.FullName | Where-Object { $_ -match "^#" } | Select-Object -First 1 | ForEach-Object { $_ -replace "#", "" }

    # Create the radio button
    $radioButton = New-Object System.Windows.Forms.RadioButton
    $radioButton.Text = $radioButtonText
    $radioButton.Tag = $configFile.FullName
    $radioButton.Location = New-Object System.Drawing.Point($radioButtonLeft, $radioButtonTop)
    $radioButton.Size = New-Object System.Drawing.Size(250, 20)
    $radioButtonTop += $radioButton.Height + $radioButtonMargin

    # $radioButton.Add_Click({
    #     $clickedRadioButton = $this
    #     & $clickedRadioButton.Tag
    # })
    Write-Host "$configFile.FullName"

    $OnionConfigGroupBox.Controls.Add($radioButton)
}

# Resize the OnionConfigGroupBox based on the radio buttons
# $OnionConfigGroupBox.Height = $radioButtonTop + $radioButtonMargin




# $InstallUpdateRadioButton3 = New-Object System.Windows.Forms.RadioButton
# $InstallUpdateRadioButton3.Location = New-Object System.Drawing.Point(20, 120)
# $InstallUpdateRadioButton3.Size = New-Object System.Drawing.Size(380, 20)
# $InstallUpdateRadioButton3.Text = "Install Onion on existing SD card"
# $InstallUpdateGroupBox.Controls.Add($InstallUpdateRadioButton3)
# $tooltip.SetToolTip($InstallUpdateRadioButton3, "This will move your current SD card files in`na sub directory and install a new Onion on your SD Card.`nThis option is useful for testing and allows an`neasy roll back if needed.")

# Tab "Backup or Restore Onion"
$BackupRestoreTab = New-Object System.Windows.Forms.TabPage
$BackupRestoreTab.Text = "Backup or Restore Onion"
$TabControl.TabPages.Add($BackupRestoreTab)

# Create GroupBox control for the "Backup or Restore Onion" tab
$BackupRestoreGroupBox = New-Object System.Windows.Forms.GroupBox
$BackupRestoreGroupBox.Location = New-Object System.Drawing.Point(20, 20)
$BackupRestoreGroupBox.Size = New-Object System.Drawing.Size(440, 200)
$BackupRestoreTab.Controls.Add($BackupRestoreGroupBox)

# Add radio buttons to the GroupBox
$BackupRestoreRadioButton1 = New-Object System.Windows.Forms.RadioButton
$BackupRestoreRadioButton1.Location = New-Object System.Drawing.Point(20, 30)
$BackupRestoreRadioButton1.Size = New-Object System.Drawing.Size(250, 20)
$BackupRestoreRadioButton1.Text = "Backup Onion or Stock SD card data"
$BackupRestoreGroupBox.Controls.Add($BackupRestoreRadioButton1)

$BackupRestoreRadioButton2 = New-Object System.Windows.Forms.RadioButton
$BackupRestoreRadioButton2.Location = New-Object System.Drawing.Point(20, 60)
$BackupRestoreRadioButton2.Size = New-Object System.Drawing.Size(250, 20)
$BackupRestoreRadioButton2.Text = "Restore a backup on Onion"
$BackupRestoreGroupBox.Controls.Add($BackupRestoreRadioButton2)

# Tab "Other Tools"
$OtherToolsTab = New-Object System.Windows.Forms.TabPage
$OtherToolsTab.Text = "SD card tools"
$TabControl.TabPages.Add($OtherToolsTab)

# Create GroupBox control for the "Other Tools" tab
$OtherToolsGroupBox = New-Object System.Windows.Forms.GroupBox
$OtherToolsGroupBox.Location = New-Object System.Drawing.Point(20, 20)
$OtherToolsGroupBox.Size = New-Object System.Drawing.Size(440, 200)
$OtherToolsTab.Controls.Add($OtherToolsGroupBox)

# Add radio buttons to the GroupBox
# $OtherToolsRadioButton1 = New-Object System.Windows.Forms.RadioButton
# $OtherToolsRadioButton1.Location = New-Object System.Drawing.Point(20, 30)
# $OtherToolsRadioButton1.Size = New-Object System.Drawing.Size(250, 20)
# $OtherToolsRadioButton1.Text = "Save/Restore image disk"
# $OtherToolsGroupBox.Controls.Add($OtherToolsRadioButton1)

$OtherToolsRadioButton2 = New-Object System.Windows.Forms.RadioButton
$OtherToolsRadioButton2.Location = New-Object System.Drawing.Point(20, 30)
$OtherToolsRadioButton2.Size = New-Object System.Drawing.Size(250, 20)
$OtherToolsRadioButton2.Text = "Format SD card in FAT32"
$OtherToolsGroupBox.Controls.Add($OtherToolsRadioButton2)

$OtherToolsRadioButton3 = New-Object System.Windows.Forms.RadioButton
$OtherToolsRadioButton3.Location = New-Object System.Drawing.Point(20, 60)
$OtherToolsRadioButton3.Size = New-Object System.Drawing.Size(250, 20)
$OtherToolsRadioButton3.Text = "Check for errors (chkdsk)"
$OtherToolsGroupBox.Controls.Add($OtherToolsRadioButton3)


# Tab "About"
$AboutTab = New-Object System.Windows.Forms.TabPage
$AboutTab.Text = "About"
$TabControl.TabPages.Add($AboutTab)

# Create Label control for the "About" tab
$AboutLabel = New-Object System.Windows.Forms.Label
$AboutLabel.Text = "Onion Desktop Tools $currentVersion`nBy Schmurtz (Onion Team)`n-----------------------`nSchmurtz Sponsors :"    #`n`n`n-----------------------`nOnion Team Sponsors :
$AboutLabel.Location = New-Object System.Drawing.Point(20, 20)
$AboutLabel.Size = New-Object System.Drawing.Size(200, 70)
$AboutTab.Controls.Add($AboutLabel)

# Create PictureBox control for the Patreon logo
$PatreonLogo = New-Object System.Windows.Forms.PictureBox
$PatreonLogo.ImageLocation = "tools\res\patreon.jpg" 
$PatreonLogo.Location = New-Object System.Drawing.Point(20, 80)
$PatreonLogo.Size = New-Object System.Drawing.Size(100, 50)
$PatreonLogo.SizeMode = [System.Windows.Forms.PictureBoxSizeMode]::Zoom
$PatreonLogo.Cursor = [System.Windows.Forms.Cursors]::Hand
$PatreonLogo.Add_Click({
        Start-Process "https://www.patreon.com/schmurtz"
    })
$AboutTab.Controls.Add($PatreonLogo)

$coffeeLogo = New-Object System.Windows.Forms.PictureBox
$coffeeLogo.ImageLocation = "tools\res\buymeacoffee.jpg" 
$coffeeLogo.Location = New-Object System.Drawing.Point(130, 80)
$coffeeLogo.Size = New-Object System.Drawing.Size(100, 50)
$coffeeLogo.SizeMode = [System.Windows.Forms.PictureBoxSizeMode]::Zoom
$coffeeLogo.Cursor = [System.Windows.Forms.Cursors]::Hand
$coffeeLogo.Add_Click({
        Start-Process "https://www.buymeacoffee.com/schmurtz"
    })

$AboutTab.Controls.Add($coffeeLogo)


# Create Label control for the "About" tab
$AboutLabel = New-Object System.Windows.Forms.Label
$AboutLabel.Text = "-----------------------`nOnion Team Sponsors :"
$AboutLabel.Location = New-Object System.Drawing.Point(20, 135)
$AboutLabel.Size = New-Object System.Drawing.Size(200, 35)
$AboutTab.Controls.Add($AboutLabel)


# Create PictureBox control for the Patreon logo
$githubLogo = New-Object System.Windows.Forms.PictureBox
$githubLogo.ImageLocation = "tools\res\github.jpg" 
$githubLogo.Location = New-Object System.Drawing.Point(20, 160)
$githubLogo.Size = New-Object System.Drawing.Size(100, 50)
$githubLogo.SizeMode = [System.Windows.Forms.PictureBoxSizeMode]::Zoom
$githubLogo.Cursor = [System.Windows.Forms.Cursors]::Hand
$githubLogo.Add_Click({
        Start-Process "https://github.com/sponsors/Aemiii91"
    })
$AboutTab.Controls.Add($githubLogo)

$kofiLogo = New-Object System.Windows.Forms.PictureBox
$kofiLogo.ImageLocation = "tools\res\kofi.jpg" 
$kofiLogo.Location = New-Object System.Drawing.Point(130, 160)
$kofiLogo.Size = New-Object System.Drawing.Size(100, 50)
$kofiLogo.SizeMode = [System.Windows.Forms.PictureBoxSizeMode]::Zoom
$kofiLogo.Cursor = [System.Windows.Forms.Cursors]::Hand
$kofiLogo.Add_Click({
        Start-Process "https://ko-fi.com/Aemiii91"
    })

$AboutTab.Controls.Add($kofiLogo)

# Create HyperlinkLabel control for the Onion Documentation link
$OnionDocLink = New-Object System.Windows.Forms.LinkLabel
$OnionDocLink.Text = "Onion Documentation"
$OnionDocLink.Location = New-Object System.Drawing.Point(20, 220)
$OnionDocLink.Size = New-Object System.Drawing.Size(200, 20)
$OnionDocLink.LinkBehavior = [System.Windows.Forms.LinkBehavior]::HoverUnderline
$OnionDocLink.Cursor = [System.Windows.Forms.Cursors]::Hand
$OnionDocLink.Add_Click({
        Start-Process "https://github.com/OnionUI/Onion/wiki"
    })
$AboutTab.Controls.Add($OnionDocLink)


# Create "OK" button
$OKButton = New-Object System.Windows.Forms.Button
$OKButton.Location = New-Object System.Drawing.Point(350, 200)
$OKButton.Size = New-Object System.Drawing.Size(75, 23)
$OKButton.Text = "OK"
$OKButton.Add_Click($OKButton_Click)
$Form.Controls.Add($OKButton)

# Add the TabControl control to the main window
$Form.Controls.Add($TabControl)


# Create a PictureBox control for the image
$EjectImg = New-Object System.Windows.Forms.PictureBox
$EjectImg.ImageLocation = "tools\res\eject.png" 
$EjectImg.Location = New-Object System.Drawing.Point(460, 255)
$EjectImg.SizeMode = [System.Windows.Forms.PictureBoxSizeMode]::AutoSize
$EjectImg.Cursor = [System.Windows.Forms.Cursors]::Hand
$EjectImg.Add_Click({
        $CurrentDrive = Get_Drive "Select a drive to eject"
        if ($CurrentDrive -ne $null) {
            write-host "Ejecting drive $($CurrentDrive[1]):"
            $argument = "$($CurrentDrive[1]):  -f -d -b"
            Start-Process -FilePath "tools\RemoveDrive.exe" -ArgumentList $argument -WorkingDirectory $PSScriptRoot -WindowStyle Hidden
        }
    })
$form.Controls.Add($EjectImg)
$EjectImg.BringToFront()

# Show the window
$Form.ShowDialog()
