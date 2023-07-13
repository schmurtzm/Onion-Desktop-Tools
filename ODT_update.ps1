$ScriptPath = $MyInvocation.MyCommand.Path
$ScriptDirectory = Split-Path $ScriptPath -Parent
Set-Location -Path $ScriptDirectory


Add-Type -AssemblyName System.Windows.Forms

$sysdir = ".\update"
$GITHUB_REPOSITORY = "Schmurtzm/Onion-Desktop-Tools"    



function GetVersion($version) {
    ($version -replace "[a-zA-Z]" -split '\.' | ForEach-Object { [int]$_ }) -join ''
}

# Function to fetch version information and populate the form
function Populate-Version {
 


    
    $global:Stable_assets_info = Invoke-RestMethod -Uri "https://api.github.com/repos/$GITHUB_REPOSITORY/releases/latest" -Method Get -UseBasicParsing
    $Stable_asset = $global:Stable_assets_info.assets | Where-Object { $_.name -like "*Onion-*" }
    $Stable_FullVersion = $Stable_asset.name -replace "^Onion-|" -replace "\.zip$"
    $Stable_Version = $Stable_FullVersion -replace "-dev.*$"
    $Stable_SizeMB = [math]::Round($Stable_asset.size / 1MB, 2)
    $Stable_DescriptionUrl = $global:Stable_assets_info.html_url.Trim('"')
    $Stable_url = $Stable_asset.browser_download_url.Trim('"')
    $Stable_FileName = $Stable_url.Split("/")[-1]

    $StableRadioButton.Text = "Stable (Version: $Stable_Version, Size: $Stable_SizeMB MB)"
    $StableInfoButton.Tag = $Stable_DescriptionUrl


    if (Test-Path downloads\$Stable_FileName) {
        $Downloaded_size = Get-Item -Path downloads\$Stable_FileName | Select-Object -ExpandProperty Length
        if ($Downloaded_size -eq $Stable_asset.size) {
            Write-Host "Stable file size already OK ! ($Downloaded_size Bytes)"
            $StableRadioButton.Enabled = 0
        }
        else {
            Write-Host "`n`nExisting Stable file has wrong size:`n` $Downloaded_size instead of $size`nDownloading...`n"
        }
    } 

    if ($StableRadioButton.Enabled -eq 0) {
        $DL_Lbl.Text = "All Onion versions are up to date."
        $DownloadButton.Enabled = 0
        $timer.Start()
    }


}

# Function to handle the Download button click event
function Download-Button_Click {

    $DownloadButton.enabled = 0
    $Downloaded_size = 0

    if ($BetaRadioButton.Checked) {
        $selectedVersion = "beta"
    }
    else {
        $selectedVersion = "stable"
    }

    # Fetch the information of the selected version
    if ($selectedVersion -eq "beta") {
        #$assets_info = (Invoke-RestMethod -Uri "https://api.github.com/repos/$GITHUB_REPOSITORY/releases" -Method Get -UseBasicParsing) | Where-Object { $_.prerelease } | Select-Object -First 1
        $assets_info = $global:Beta_assets_info
    }
    else {
        #$assets_info = Invoke-RestMethod -Uri "https://api.github.com/repos/$GITHUB_REPOSITORY/releases/latest" -Method Get -UseBasicParsing
        $assets_info = $global:Stable_assets_info
    }

    $asset = $assets_info.assets | Where-Object { $_.name -like "*Onion-*" }
    $url = $asset.browser_download_url.Trim('"')
    $FullVersion = $asset.name -replace "^Onion-|" -replace "\.zip$"
    $Version = $FullVersion -replace "-dev.*$"
    $size = $asset.size
    $SizeMB = [math]::Round($size / 1MB, 2)
    $info = $assets_info.body

    # Display the selected version information
    #$message = "Version : $Version (Channel: $selectedVersion)`nSize : $SizeMB MB`nURL : $url"
    #[System.Windows.Forms.MessageBox]::Show($message, "Download Information", "OK", "Information")



    Write-Host "`n`n== Downloading Onion $Version ($selectedVersion channel) ==" 
    #$ProgressPreference = 'SilentlyContinue'
    #Invoke-WebRequest -Uri $url -OutFile (Join-Path $downloadPath "$Version.zip")
    #$command = "Invoke-WebRequest -Uri '$url' -OutFile (Join-Path '$downloadPath' '$Version.zip')"
    #Write-Host $command
    # Invoke-Expression -Command $command


    ##############################

    # Déterminer le nom du fichier Ã  partir de l'URL
    $downloadPath = Join-Path $ScriptDirectory "downloads"
    New-Item -ItemType Directory -Force -Path $downloadPath | Out-Null
    $Update_FileName = $url.Split("/")[-1]
    $Update_FullPath = Get-Item -Path "downloads\$Update_FileName"

    Write-Host "url $url" 
    Write-Host "Update_FullPath $Update_FullPath" 

    if (Test-Path downloads\$Update_FileName) {
        $Downloaded_size = Get-Item -Path downloads\$Update_FileName | Select-Object -ExpandProperty Length
    }
    else { $Downloaded_size = 0 }
    
    if ($Downloaded_size -eq $size) {
        Write-Host "File size already OK ! ($Downloaded_size Bytes)"
        $DL_Lbl.Text = "File size already OK ! ($Downloaded_size Bytes)"
        $DownloadButton.enabled = 1
        return 
        #Start-Sleep -Seconds 3
    }
    else {
        Write-Host "`n`nExisting file has wrong size:`n` $Downloaded_size instead of $size`nDownloading...`n"
    }
    

    # Lancer wget en arriére-plan pour télécharger le fichier 
    # invisible download window
    # $wgetProcess = Start-Process -FilePath "wget" -ArgumentList "q", "-nv", "-O", $fileName, $url -WindowStyle Hidden -PassThru

    #mini download window :
    #$wgetProcess = Start-Process -FilePath "cmd" -ArgumentList " /c mode con:cols=150 lines=1 & tools\wget" , "-P .\downloads" , "-O $fileName", $url -PassThru

    $progressBar.visible = 1
    $wgetProcess = Start-Process -FilePath "cmd" -ArgumentList "    /c mode con:cols=150 lines=1 & tools\wget", "-O `"downloads\$Update_FileName`"", $url -PassThru




    # Tant que wget est en arriére-plan, afficher la taille du fichier actuel
    while (!$wgetProcess.HasExited) {
        #$fileSize = $Update_FullPath | Select-Object -ExpandProperty Length
        if (Test-Path downloads\$Update_FileName) {
            $fileSize = Get-Item -Path downloads\$Update_FileName | Select-Object -ExpandProperty Length
        }
        else { $fileSize = 0 }
        #$fileSize = downloads\$Update_FileName.Length
        $progress = [math]::Round(($fileSize / $size) * 100)  # Calculer la progression en pourcentage
        $progressBar.Value = $progress  # Mettre à jour la valeur de la barre de progression
        Start-Sleep -Milliseconds 1000  # Attendre une demi-seconde
    }

    ##############################


    Write-Host "`n`n=================== Download done ===================`n"

    $DownloadButton.enabled = 1
    $progressBar.Value = 0
    $progressBar.visible = 0
    
    if (Test-Path downloads\$Update_FileName) {
        $Downloaded_size = Get-Item -Path downloads\$Update_FileName | Select-Object -ExpandProperty Length
    }
    else { $Downloaded_size = 0 }
    if ($Downloaded_size -eq $size) {
        Write-Host "File size OK! ($Downloaded_size)"
        $DL_Lbl.Text = "Download successful."
        #Start-Sleep -Seconds 3
    }
    else {
        Write-Host "`n`nError: Wrong download size:`n` $Downloaded_size instead of $size`n"
        $DL_Lbl.Text = "Download failed."
    }

}

# Create a new instance of Windows Form
$form = New-Object System.Windows.Forms.Form
$form.Text = "Onion Downloader"
$form.Size = New-Object System.Drawing.Size(600, 200)
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedSingle
$form.MaximizeBox = $false
$form.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen


# Create the Stable radio button
$StableRadioButton = New-Object System.Windows.Forms.RadioButton
$StableRadioButton.Text = "Stable"
$StableRadioButton.Location = New-Object System.Drawing.Point(20, 20)
$StableRadioButton.Size = New-Object System.Drawing.Size(500, 20)
$StableRadioButton.Checked = $true
$form.Controls.Add($StableRadioButton)


# Create the Beta radio button
$BetaRadioButton = New-Object System.Windows.Forms.RadioButton
$BetaRadioButton.Text = "Beta"
$BetaRadioButton.Location = New-Object System.Drawing.Point(20, 50)
$BetaRadioButton.Size = New-Object System.Drawing.Size(500, 20)
$form.Controls.Add($BetaRadioButton)

# Create the Stable info button
$StableInfoButton = New-Object System.Windows.Forms.Button
$StableInfoButton.Text = "i"
$StableInfoButton.Location = New-Object System.Drawing.Point(530, 20)
$StableInfoButton.Size = New-Object System.Drawing.Size(20, 20)
$StableInfoButton.Font = New-Object System.Drawing.Font("Arial", 10, [System.Drawing.FontStyle]::Bold)
$StableInfoButton.Add_Click({ Start-Process $StableInfoButton.Tag })
$form.Controls.Add($StableInfoButton)

# Create the Beta info button
$BetaInfoButton = New-Object System.Windows.Forms.Button
$BetaInfoButton.Text = "i"
$BetaInfoButton.Location = New-Object System.Drawing.Point(530, 50)
$BetaInfoButton.Size = New-Object System.Drawing.Size(20, 20)
$BetaInfoButton.Font = New-Object System.Drawing.Font("Arial", 10, [System.Drawing.FontStyle]::Bold)
$BetaInfoButton.Add_Click({ Start-Process $BetaInfoButton.Tag })
$form.Controls.Add($BetaInfoButton)

# Create the Download button
$DownloadButton = New-Object System.Windows.Forms.Button
$DownloadButton.Text = "Download"
$DownloadButton.Location = New-Object System.Drawing.Point(20, 80)
$DownloadButton.Size = New-Object System.Drawing.Size(100, 23)
$DownloadButton.Add_Click({ Download-Button_Click })
$form.Controls.Add($DownloadButton)

# Créer la barre de progression dans le formulaire
$progressBar = New-Object System.Windows.Forms.ProgressBar
$progressBar.Location = New-Object System.Drawing.Point(20, 110)
$progressBar.Size = New-Object System.Drawing.Size(500, 23)
$progressBar.visible = 0
$form.Controls.Add($progressBar)

$DL_Lbl = New-Object System.Windows.Forms.Label
$DL_Lbl.Location = New-Object System.Drawing.Point(20, 110)
$DL_Lbl.Size = New-Object System.Drawing.Size(500, 46)
$form.Controls.Add($DL_Lbl)

$tooltip = New-Object System.Windows.Forms.ToolTip
$tooltip.SetToolTip($StableInfoButton, "Show release notes.")
$tooltip.SetToolTip($BetaInfoButton, "Show release notes.")

$timer = New-Object System.Windows.Forms.Timer
$timer.Interval = 1000

$timer.Add_Tick({
        # Utiliser le modificateur script pour accéder à la variable globale
        $script:counter -= 1
        $DL_Lbl.Text = "All Onion versions are up to date.`nClosing in $script:counter s"
        if ($script:counter -eq 0) {
            $timer.Stop()
            $form.Close()
        }
    })


#Write-Host "Beta Release Name: $global:Beta_assets_info"
$script:counter = 6
# Populate version information
Populate-Version

# Show the form
$iconPath = Join-Path -Path $PSScriptRoot -ChildPath "tools\res\onion.ico"
$icon = New-Object System.Drawing.Icon($iconPath)
$form.Icon = $icon
$result = $form.ShowDialog()
$form.Dispose()

$timer.Stop()
