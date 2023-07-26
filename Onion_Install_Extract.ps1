param (
    [Parameter(Mandatory = $false)]
    [string]$Update_File,
    [Parameter(Mandatory = $false)]
    [string]$Target
)



# $Target = "G:"
$script:SdCardState = ""
$ScriptPath = $MyInvocation.MyCommand.Path
$ScriptDirectory = Split-Path $ScriptPath -Parent
Set-Location -Path $ScriptDirectory

if (-not $Target) {
    . "$PSScriptRoot\Disk_selector.ps1"
    $selectedTagSplitted = $selectedTag.Split(",")
    $Drive_Number = $($selectedTagSplitted[0])
    $Drive_Letter = $($selectedTagSplitted[1])
    $Target = "$Drive_Letter`:"
}

$7zPath = "tools\7z.exe"
# Vérification de l'espace disponible sur le lecteur cible
$driveInfo = Get-PSDrive -PSProvider 'FileSystem' | Where-Object { $_.Root -eq "$Target\" }
$freeSpace = $driveInfo.Free


# Vérification de la disponibilité de l'espace nécessaire pour l'extraction


function Get_SDcardType {
    $driveLetter = $Target.Replace(":", "")


    $label_right.Text += "`r`n`r`n`------------------------ SD CARD information ------------------------`r`n"

    $label_right.Text += "`r`nDrive letter : $Target"

    $volume = Get-Volume -DriveLetter "$driveLetter"
    if ($volume.FileSystemType -eq $null) {
        Write-Host "Impossible to get current file system"
        $label_right.Text += "`r`n`r`n`r`nImpossible to get current file system"
        $label_right.Text += "`r`n Check that your SD card is formated in FAT32"
        $label_right.Text += "`r`n You can try to repair .net frame work : "
        $label_right.Text += "`r`n  https://aka.ms/DotnetRepairTool`r`n`r`n"
    }
    elseif ($volume.FileSystemType -ne "FAT32") {
        Write-Host "File system type: $($volume.FileSystemType)"
        Write-Host "⚠ This file system is not supported by Onion. ⚠"
        $label_right.Text += "`r`nFile system type: $($volume.FileSystemType)"
        $label_right.Text += "`r`n⚠ This file system is not supported by Onion. ⚠"
        $label_right.Text += "`r`n(You can use Onion Installer to format your SD card in FAT32)"
    }
    elseif ($volume.FileSystemType -eq "FAT32") {
        Write-Host "File system type is compatible with Onion: $($volume.FileSystemType)"
        $label_right.Text += "`r`nFile system type is compatible with Onion: $($volume.FileSystemType)"

    }

    $messageBoxText = ""

    if (Test-Path -Path "${Target}\") {
        $items = Get-ChildItem -Path "$($Target)\"
        if ($items.Count -eq 0) {
            #################### empty partition ####################
            Write-Host "Blank SD card."
            $label_right.Text += "`r`nEmpty SD card"
            $script:SdCardState = "empty"
        }
        else {
            #################### previous Onion ####################
            Write-Host "The SD card contains files/folders."
            $label_right.Text += "`r`n⚠ The SD card already contains files/folders :"
            Write-Host "Looking for previous Onion installation version..."

            $verionfilePath = "${Target}\.tmp_update\bin\installUI"
            if (Test-Path -Path "${Target}\.tmp_update\bin\installUI" -PathType Leaf) {
                $versionRegex = '--version\s+(.*?)\s'
                $script:SdCard_Version = [regex]::Match((tools\strings.exe ${Target}\.tmp_update\bin\installUI), $versionRegex).Groups[1].Value
                if ($script:SdCard_Version -eq "") {
                    # if we don't get Onion version from InstallUI, we get it from version.txt
                    $verionfilePath = "${Target}\.tmp_update\onionVersion\version.txt"
                    if (Test-Path -Path $verionfilePath -PathType Leaf) {
                        $script:SdCard_Version = Get-Content -Path $verionfilePath -Raw
                    }
                }
            
                Write-Host "Onion version $script:SdCard_Version already installed on this SD card."
                $label_right.Text += "`r`nOnion $script:SdCard_Version on ${Target}"
                $script:SdCardState = "Onion"
            }
            elseif ((Test-Path -Path "${Target}\.tmp_update") -and (Test-Path -Path "${Target}\miyoo\app\.tmp_update\onion.pak")) {
                #################### Fresh Onion install files (not executed on MM) ####################
                $versionRegex = '--version\s+(.*?)\s'
                $script:SdCard_Version = [regex]::Match((tools\strings.exe ${Target}\miyoo\app\.tmp_update\bin\installUI), $versionRegex).Groups[1].Value
                if ($script:SdCard_Version -eq "") {
                    $script:versiSdCard_Versionon = "(unknown version)"
                }
                Write-Host "It seems to be and non installed Onion version"
                $label_right.Text += "`r`nFresh Onion install files $script:SdCard_Version on ${Target}"
                $script:SdCardState = "Onion_InstallPending"
            }
            elseif (Test-Path -Path "${Target}\RApp\") {
                #################### previous Stock ####################
                Write-Host "It seems to be a stock SD card from Miyoo"
                $label_right.Text += "`r`nMiyoo Stock OS on ${Target}"
                $script:SdCardState = "Stock"
            }
            else {
                #################### unknown files ####################
                Write-Host "Unidentified : Not Onion or Stock"
                $label_right.Text += "`r`nNot Onion or Stock"
                $script:SdCardState = "Other"
            }


    
        }

        $label_right.Text += "`r`nSpace available: $([Math]::Round($freeSpace / 1MB)) MB"
    }

}





function Button_Click {




    $Update_File = $flowLayoutPanel.Controls | Where-Object { $_.Checked } | Select-Object -ExpandProperty Text

    if (-not $Update_File) {
        # Check if $Update_File is empty
        Write-Host "No file selected."
        return
    }

    Write-Host "Selected file: $Update_File"
    Write-Host "Destination: $Target"
        


    $label_right.Text += "`r`n`r`n`------------------- EXTRACTION OF ONION -------------------`r`n"
    $label_right.Text += "`r`nSelected file: `"$Update_File`"`r`nDestination: $Target"
    $form.Refresh()

    $output = & $7zPath l "downloads\$Update_File" | Select-String 'files,' | Select-Object -Last 1
    if ($output) {
        $uncompressedSize = ($output.Line -split '\s+')[2]
        $uncompressedSize
    }
    else {
        Write-Host "Unable to recover decompressed zip file size."
    }

    Write-Host "Space required: $([Math]::Round($uncompressedSize / 1MB)) MB`nSpace available: $([Math]::Round($freeSpace / 1MB)) MB"

    if (($freeSpace -gt $uncompressedSize) -or ($freeSpace -eq $null)) {
        # when WMI is broken $freeSpace is null
        



        If ($script:SdCardState -eq "empty") {
            $messageBoxText = "You're about to install $Update_File.`n" +
            "Are you sure that you want install it on ${Target} ?`n"
        }
        elseif ($script:SdCardState -eq "Onion") {
            $messageBoxText = "You're about to upgrade Onion OS`n`"$script:SdCard_Version`" to `"$Update_File`".`n`n" +
            "Are you sure that you want update ?`n" +
            "(Saves, rom and configuration will be conserved)"
        
        }
        elseif ($script:SdCardState -eq "Onion_InstallPending") {
            $messageBoxText = "You're about to upgrade Onion OS ($script:SdCard_Version) which has never been used) with $Update_File.`n`n" +
            "If this previous install doesn't contains any data then you'll prefer to format your SD card and start again.`n`n" +
            "Are you sure that you want update ?`n"
    
        }
        elseif ($script:SdCardState -eq "Stock") {
            $messageBoxText = "You're about to upgrade a stock OS with $Update_File.`n`n" +
            "!!! it is clearly not recommended/supported and you could have many side effects.`n`n" +
            "Please use a new and guenuine SD card to install Onion`n" +
            "Then copy the data from Stock to this new SD card thanks to`n" +
            "the backup/restore functionalities of Onion installer.`n`n" +
            "Are you sure that you want to force this not recommanded installation ?`n`n"
        }
        elseif ($script:SdCardState -eq "Other") {
            $messageBoxText = "!!! You're about to install $Update_File on a non empty SD card.`n" +
            "It is possible to install Onion on a SD card which already contains some data however it's not recommended`n" +
            "If your SD card doesn't contains any important data then you'll prefer to format your SD card and start again.`n`n" +
            "Are you sure that you want to force this installation ?`n"
        }
        else {
            $messageBoxText = "You're about to install `"$Update_File`".`n" +
            "Are you sure that you want install it on ${Target} ? $script:SdCardState `n"


        }


        $messageBoxCaption = "Installation Confirmation"
        $messageBoxButtons = [System.Windows.Forms.MessageBoxButtons]::YesNo
        $messageBoxIcon = [System.Windows.Forms.MessageBoxIcon]::Warning
        $result = [System.Windows.Forms.MessageBox]::Show($messageBoxText, $messageBoxCaption, $messageBoxButtons, $messageBoxIcon)

        if ($result -eq [System.Windows.Forms.DialogResult]::Yes) {
         
            $button.Enabled = 0

            $label_right.Text += "`r`nExtraction in progress..."
 
            $label_right.SelectionStart = $label_right.Text.Length
            $label_right.ScrollToCaret()

            $wgetProcess = Start-Process -FilePath "cmd" -ArgumentList "/c @title extracting $Update_File to $Target & mode con:cols=80 lines=1 & $7zPath x -y -aoa `"downloads\$Update_File`" -o`"$Target\`"" -PassThru
            $wgetProcess.WaitForExit()
            $exitCode = $wgetProcess.ExitCode
            # while (!$wgetProcess.HasExited) {
            #     Start-Sleep -Milliseconds 1000
            # }
            

            if ($exitCode -eq 0) {
                Write-Host "Decompression successful."
                Write-Host "`n`nUpdate $Release_Version applied.`nInsert SD card in your Miyoo and start it to run installation!`n"
                $label_right.Text += "`r`nExtraction successful !`r`nYou can now close this Windows.`r`nInsert this SD card in your Miyoo to start Installation."
            }
            else {
                Write-Host "`n`nError: Something went wrong during decompression.`nTry to run OTA update again or make a manual update.`nInstallation stopped."
                $label_right.Text += "`r`nError: Something went wrong during decompression.`r`nTry to run OTA update again or make a manual update.`r`nInstallation stopped."
            }
            # else {
            #     Write-Host "Insufficient space on $Target drive to extract file."
            #     $label_right.Text += "`r`nInsufficient space on $Target drive to extract file."
            # }

            $button.Enabled = 1

        }
        else {
            Write-Host "`n`nInstallation canceled by user."
            $label_right.Text += "`r`nInstallation canceled by user."
        }

        $form.Refresh()
        $label_right.SelectionStart = $label_right.Text.Length
        $label_right.ScrollToCaret()
    }
    else {
        Write-Host "`n`nError: No enough space for decompression."
        $label_right.Text += "`r`nError: No enough space for decompression.`r`nSpace required: $([Math]::Round($uncompressedSize / 1MB)) MB`r`nSpace available: $([Math]::Round($freeSpace / 1MB)) MB`r`nInstallation canceled."
    }
}

if (-not $Update_File) {
    # Afficher un Windows Form pour sélectionner le fichier à extraire
    Add-Type -AssemblyName System.Windows.Forms

    $font = New-Object System.Drawing.Font("Microsoft Sans Serif", 8.25) 
    $bold = New-Object System.Drawing.Font("Microsoft Sans Serif", 8.25, [System.Drawing.FontStyle]::Bold)

    $form = New-Object System.Windows.Forms.Form
    $form.Text = "Onion Extractor"
    $form.Size = New-Object System.Drawing.Size(650, 380)
    $form.StartPosition = "CenterScreen"
    $iconPath = Join-Path -Path $PSScriptRoot -ChildPath "tools\res\onion.ico"
    $icon = New-Object System.Drawing.Icon($iconPath)
    $form.Icon = $icon

    $label = New-Object System.Windows.Forms.Label
    $label.Location = New-Object System.Drawing.Point(10, 20)
    $label.Size = New-Object System.Drawing.Size(300, 20)
    $label.Text = "Select the Onion version to install:"
    $label.Font = $bold 
    $label.Anchor = [System.Windows.Forms.AnchorStyles]::Top -bor [System.Windows.Forms.AnchorStyles]::Left -bor [System.Windows.Forms.AnchorStyles]::Right
    $form.Controls.Add($label)

    $label_right = New-Object System.Windows.Forms.TextBox
    $label_right.Multiline = $true
    $label_right.ReadOnly = $true
    $label_right.ScrollBars = "Vertical"
    $label_right.Location = New-Object System.Drawing.Point(330, 20)
    $label_right.Size = New-Object System.Drawing.Size(280, 300)
    
    $label_right.Font = $font
    $label_right.Anchor = [System.Windows.Forms.AnchorStyles]::Top -bor [System.Windows.Forms.AnchorStyles]::Left -bor [System.Windows.Forms.AnchorStyles]::Right
    $form.Controls.Add($label_right)
    $currentFont = $label_right.Font


    $panel = New-Object System.Windows.Forms.Panel
    $panel.Location = New-Object System.Drawing.Point(10, 60)
    $panel.Size = New-Object System.Drawing.Size(300, 200)
    $panel.AutoScroll = $true
    $form.Controls.Add($panel)

    $flowLayoutPanel = New-Object System.Windows.Forms.FlowLayoutPanel
    $flowLayoutPanel.Location = New-Object System.Drawing.Point(0, 0)
    $flowLayoutPanel.AutoSize = $true  # Mettre à true pour ajuster automatiquement la taille du panneau
    $flowLayoutPanel.FlowDirection = "TopDown"
    $panel.Controls.Add($flowLayoutPanel)

    $files = Get-ChildItem "$ScriptDirectory\downloads" -Filter "*.zip" -File
    foreach ($file in $files) {
        $radioButton = New-Object System.Windows.Forms.RadioButton
        $radioButton.AutoSize = $true
        $radioButton.Text = $file.Name
        $flowLayoutPanel.Controls.Add($radioButton)
    }

    $button = New-Object System.Windows.Forms.Button
    $button.Location = New-Object System.Drawing.Point(10, 300)
    $button.Size = New-Object System.Drawing.Size(75, 23)
    $button.Add_Click({ Button_Click })
    $button.Text = "OK"
    $form.Controls.Add($button)

    Get_SDcardType

    $result = $form.ShowDialog()

    if ($result -ne [System.Windows.Forms.DialogResult]::OK) {
        Write-Host "No update file selected. Exiting."
        exit 1
    }

    $selectedFile = $flowLayoutPanel.Controls | Where-Object { $_ -is [System.Windows.Forms.RadioButton] -and $_.Checked } | Select-Object -First 1
    if ($selectedFile -eq $null) {
        Write-Host "No update file selected. Exiting."
        exit 1
    }

    $Update_File = $selectedFile.Text
}
