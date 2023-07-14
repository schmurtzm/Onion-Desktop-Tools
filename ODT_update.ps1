Add-Type -AssemblyName System.Windows.Forms

# GitHub API URL
$apiUrl = "https://api.github.com/repos/Schmurtzm/Onion-Desktop-Tools/releases/latest"

# Get the information of the latest release from GitHub API
$releaseInfo = Invoke-RestMethod -Uri $apiUrl

# Get the version number from the tag_name in the API response
if ($releaseInfo -and $releaseInfo.tag_name) {
    $latestVersion = $releaseInfo.tag_name
} else {
    Write-Host "Failed to retrieve the latest version from GitHub API. No action required."
    return
}

# Read the Menu.ps1 file and get the version number from the first line
$menuFilePath = "Menu.ps1"
$menuContent = Get-Content -Path $menuFilePath
if ($menuContent -and $menuContent[0]) {
    $currentVersion = $menuContent[0] -replace "# Onion-Desktop-Tools-"
} else {
    Write-Host "Failed to retrieve the current version from Menu.ps1 file. No action required."
    return
}

# Compare the versions
if ($latestVersion -gt $currentVersion) {
    $messageBoxText = "A newer version of Onion Desktop Tools is available:`nCurrent version: $currentVersion.`nAvailable version: $latestVersion.`n`nDo you want to download and install the new version?"



    $form = New-Object System.Windows.Forms.Form
    $form.Text = $messageBoxCaption
    $form.Width = 420
    $form.Height = 200
    $Form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::FixedSingle
    $Form.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen

    $label = New-Object System.Windows.Forms.Label
    $label.Location = New-Object System.Drawing.Point(20, 20)
    $label.Size = New-Object System.Drawing.Size(350, 60)
    $label.Text = $messageBoxText
    $form.Controls.Add($label)

    $buttonYes = New-Object System.Windows.Forms.Button
    $buttonYes.Location = New-Object System.Drawing.Point(40, 100)
    $buttonYes.Size = New-Object System.Drawing.Size(100, 30)
    $buttonYes.Text = "Yes"
    $buttonYes.DialogResult = [System.Windows.Forms.DialogResult]::Yes
    $form.Controls.Add($buttonYes)

    $buttonNo = New-Object System.Windows.Forms.Button
    $buttonNo.Location = New-Object System.Drawing.Point(160, 100)
    $buttonNo.Size = New-Object System.Drawing.Size(100, 30)
    $buttonNo.Text = "No"
    $buttonNo.DialogResult = [System.Windows.Forms.DialogResult]::No
    $form.Controls.Add($buttonNo)

    $buttonUrl = New-Object System.Windows.Forms.Button
    $buttonUrl.Location = New-Object System.Drawing.Point(280, 100)
    $buttonUrl.Size = New-Object System.Drawing.Size(100, 30)
    $buttonUrl.Text = "Show URL"
    $buttonUrl.Add_Click({ Start-Process $releaseInfo.html_url })
    $form.Controls.Add($buttonUrl)

    $form.ShowDialog() | Out-Null

    if ($form.DialogResult -eq [System.Windows.Forms.DialogResult]::Yes) {
        Write-Host "Downloading..."

        # Download the ZIP file
        $zipUrl = $releaseInfo.zipball_url
        $zipFilePath = "Onion-Desktop-Tools.zip"
        Invoke-WebRequest -Uri $zipUrl -OutFile $zipFilePath

        # Extract the contents of the ZIP file using 7-Zip
        $extractDir = "Onion-Desktop-Tools"
        & "7z.exe" x -y $zipFilePath "-o$extractDir"

        Write-Host "Download and extraction completed."
    } else {
        Write-Host "Operation canceled. No download performed."
    }
} else {
    Write-Host "The version $latestVersion is the same or lower than $currentVersion. No action required."
}
