Add-Type -AssemblyName System.Windows.Forms

function Get-WifiPassword {
    [CmdletBinding()]
    param ()
    
    begin {
        try {
            # Export all Wifi profiles and collect their XML file paths
            $ExportPath = New-Item -Path $HOME -Name ('GetWifiPassword_' + (New-Guid).Guid) -ItemType Directory
            $CurrentPath = (Get-Location).Path
            Set-Location $ExportPath
            netsh wlan export profile key=clear
            $XmlFilePaths = Get-ChildItem -Path $ExportPath -File
        }
        catch {
            Write-Error "Failed to export Wifi profiles: $($_.Exception.Message)"
            return
        }
    }
    
    process {
        $form = New-Object System.Windows.Forms.Form
        $form.Text = "Profils WiFi"
        $form.Size = New-Object System.Drawing.Size(600, 400)
        $form.StartPosition = "CenterScreen"
        $iconPath = Join-Path -Path $PSScriptRoot -ChildPath "tools\res\wifi.ico"
        $icon = New-Object System.Drawing.Icon($iconPath)
        $form.Icon = $icon
        
        $tableLayoutPanel = New-Object System.Windows.Forms.TableLayoutPanel
        $tableLayoutPanel.Dock = 'Fill'
        $tableLayoutPanel.ColumnCount = 2
        $tableLayoutPanel.ColumnStyles.Add((New-Object System.Windows.Forms.ColumnStyle([System.Windows.Forms.SizeType]::Percent, 50)))
        $tableLayoutPanel.ColumnStyles.Add((New-Object System.Windows.Forms.ColumnStyle([System.Windows.Forms.SizeType]::Percent, 50)))
        
        $wifiInfo = @() # Array to store Wifi information
        
        foreach ($XmlFilePath in $XmlFilePaths) {
            try {
                # Read the XML file and extract the Wifi profile name and password
                # $Xml = [xml](Get-Content -Path $XmlFilePath.FullName)
                ($Xml = [xml]::new()).Load((Convert-Path -LiteralPath $XmlFilePath.FullName))
    
                if ($Xml.WLANProfile -and $Xml.WLANProfile.Name -and $Xml.WLANProfile.MSM.Security.SharedKey.KeyMaterial) {
                    $name = $Xml.WLANProfile.Name
                    Write-Host "$name"
                    $password = $Xml.WLANProfile.MSM.Security.SharedKey.KeyMaterial
                    $succeed = $true
    
                    if ($succeed) {
                        $button = New-Object System.Windows.Forms.Button
                        $button.Text = $name
                        $button.Tag = @{
                            SSID     = $name
                            Password = $password
                        }
                        $button.Width = 250
                        $button.Add_Click({ 
                                $clickedButton = $this
                                $form.Tag = $clickedButton.Tag
                                $form.DialogResult = [System.Windows.Forms.DialogResult]::OK
                                $form.Close()
                            })
                        
                        $tableLayoutPanel.Controls.Add($button)
                    }
                    
                    $wifiInfo += [PSCustomObject]@{
                        Name     = $name
                        Password = $password
                        Succeed  = $succeed
                    }
                }
                else {
                    $succeed = $false
                }
            }
            catch {
                Write-Error "Failed to read Wifi profile from '$XmlFilePath': $($_.Exception.Message)"
            }
        }
        
        $form.Controls.Add($tableLayoutPanel)
        $result = $form.ShowDialog()
        if ($result -eq [System.Windows.Forms.DialogResult]::OK) {
            return $form.Tag
        }
        else {
            return $null
        }
    }
    
    end {
        Set-Location $CurrentPath
        # Remove-Item $ExportPath -Confirm:$false -Recurse
    }
}

Get-WifiPassword
