# Emulators and apps


Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName Microsoft.VisualBasic

# Variables globales
$global:rowCountWithoutColor = 0
$global:rowCountGreen = 0
$global:rowCountOrange = 0

# Function to create and populate the table
function FillTable {
    param (
        [System.Windows.Forms.DataGridView]$dataGridView,
        [string]$PackType
    )

    $PacksrootPath = "G:\App\PackageManager\data\$PackType\"

    # App\PackageManager\data\Emu\Atari - 2600 (Stella 2014)\Emu
    # App\PackageManager\data\$PackType\$PackName\$PackContent

    $PacksNames = Get-ChildItem -Path $PacksrootPath -Directory
        
    foreach ($PacksName in $PacksNames) {
        # exple : for each in "App\PackageManager\data\Emu"
        $PackContents = Get-ChildItem -Path (Join-Path -Path $PacksName.FullName -ChildPath $PackType) -Directory

        foreach ($PackContent in $PackContents) {
            # exple : for each in "App\PackageManager\data\Emu\Atari - 2600 (Stella 2014)\Emu"
  
            Write-Output "Parent Directory: $PacksName.Name, Sub Directory: $PackContent.Name"

            $row = New-Object System.Windows.Forms.DataGridViewRow
            $cell1 = New-Object System.Windows.Forms.DataGridViewTextBoxCell
            $cell2 = New-Object System.Windows.Forms.DataGridViewTextBoxCell
            $cell3 = New-Object System.Windows.Forms.DataGridViewTextBoxCell
            $cell4 = New-Object System.Windows.Forms.DataGridViewTextBoxCell
            $cell1.Value = $PacksName.Name
            $cell2.Value = $PackType
            $cell3.Value = $PackContent.Name
            $cell4.Value = ""
            $row.Cells.AddRange($cell1, $cell2, $cell3)



            $PackRomDirectory = Join-Path -Path $PacksName.FullName -ChildPath "Roms"

            if (Test-Path $PackRomDirectory -PathType Container) {
                $romSubDirectories = Get-ChildItem -Path $PackRomDirectory -Directory
                $row.Cells.Add($cell4)
                $dataGridView.Rows.Add($row)
                    
                foreach ($romSubDirectory in $romSubDirectories) {
                    $cell4.Value = $romSubDirectory.name
                }

                if (Test-Path "G:\$PackType\$PackContent" -PathType Container) {
                    Write-Output "G:\$PackType\$PackContent"
                    $row.DefaultCellStyle.BackColor = "Green"
                    $global:rowCountGreen++
                }
                else {
                    $GamesNumber = 0 
                    if (Test-Path "G:\Roms\$romSubDirectory" -PathType Container) {
                        $games = Get-ChildItem -Path "G:\Roms\$romSubDirectory"
                        $GamesNumber = $games.Count
                    }

                    if ($GamesNumber -gt 0) {
                        Write-Output "Roms: $romSubDirectory, Here!!!!"
                        $row.DefaultCellStyle.BackColor = "Orange"
                        $global:rowCountOrange++
                    }
                    else {
                        $global:rowCountWithoutColor++
                    }
                    
                }
            }
            else {
                if ( $PackContent.Name -ne "romscripts") {
                    # no roms folder, it can be an app
                    if (Test-Path "G:\$PackType\$PackContent" -PathType Container) {
                        Write-Output "G:\$PackType\$PackContent"
                        $row.DefaultCellStyle.BackColor = "Green"
                        $global:rowCountGreen++
                    }
                    else {
                        $global:rowCountWithoutColor++
                    }
                    
                    $row.Cells.Add($cell4)
                    $dataGridView.Rows.Add($row)
                }

            }
            
        }

        
        

    }

    
    $labelRowCount.Text = "Items not installed: $rowCountWithoutColor`nItems installed: $rowCountGreen`nItem not installed but roms are here: $rowCountOrange"

}

function Get-SubDirectories {
    param (
        [string]$PackType
    )

    $rootPath = "G:\App\PackageManager\data\$PackType\"
    $directories = Get-ChildItem -Path $rootPath -Directory

    foreach ($directory in $directories) {
        $PackContent = Get-ChildItem -Path (Join-Path -Path $directory.FullName -ChildPath $PackType) -Directory

        foreach ($subDirectory in $PackContent) {
            $subDirectoryName = $subDirectory.Name
            $PacksName.Name = $directory.Name

            Write-Output "Parent Directory: $PacksName.Name, Sub Directory: $subDirectoryName"
        }
    }
}

# Function to handle Rom Folder column cell click event
$DataGrid_CellDoubleClick = {
    param(
        [System.Object]$sender,
        [System.Windows.Forms.DataGridViewCellEventArgs]$e
    )

    $rowIndex = $e.RowIndex
    $columnIndex = $e.ColumnIndex

    $SelName = $dataGridView.Rows[$rowIndex].Cells[0].Value
    $SelType = $dataGridView.Rows[$rowIndex].Cells[1].Value
    $SelEmuFolder = $dataGridView.Rows[$rowIndex].Cells[2].Value
    $SelRomFolder = $dataGridView.Rows[$rowIndex].Cells[3].Value



    if ($columnIndex -eq 2) {
        #  to handle "Emu Folder" column cell click event 
        $emuFolderPath = "G:\Emu\$SelEmuFolder"
        if (Test-Path $emuFolderPath -PathType Container) {
            Invoke-Item -Path $emuFolderPath
        }
        else {
            [Microsoft.VisualBasic.Interaction]::MsgBox("Emu folder not found: $emuFolderPath", [Microsoft.VisualBasic.MsgBoxStyle]::OkOnly, "Error")
        }

    }

    if ($columnIndex -eq 3) {
        #  to handle "Rom Folder" column cell click event 
        $RomFolderPath = "G:\Roms\$SelRomFolder"
        if (Test-Path $RomFolderPath -PathType Container) {
            Invoke-Item -Path $RomFolderPath
        }
        else {
            [Microsoft.VisualBasic.Interaction]::MsgBox("Rom folder not found: $RomFolderPath", [Microsoft.VisualBasic.MsgBoxStyle]::OkOnly, "Error")
        }

    }

    $cellValue = $dataGridView.Rows[$rowIndex].Cells[$columnIndex].Value
    write-output "********************* $SelName $SelType $SelEmuFolder"

    #[System.Windows.Forms.MessageBox]::Show("Position : ($rowIndex, $columnIndex)`nContenu : $cellValue `n$SelName `n$SelType `n$SelEmuFolder")


    if ($columnIndex -eq 0) {
        #  to handle "Emu Folder" column cell click event 

        $message = "Copy content of `G:\App\PackageManager\data\$SelType\$SelName` to the root of G:"
    
        $result = [Microsoft.VisualBasic.Interaction]::MsgBox($message, [Microsoft.VisualBasic.MsgBoxStyle]::YesNo, "Confirmation")
        if ($result -eq [Microsoft.VisualBasic.MsgBoxResult]::Yes) {
            $sourcePath = "G:\App\PackageManager\data\$SelType\$SelName\*"
            $destinationPath = "G:\"
        
            Copy-Item -Path $sourcePath -Destination $destinationPath -Recurse -Force
            
        }
        & $RefreshItems
    }
}

# Function to handle "pouet" button click event
$InstallButton_Click = {
    $selectedRows = $dataGridView.SelectedRows
    if ($selectedRows.Count -eq 0) {
        Write-Host "No rows selected."
        [Microsoft.VisualBasic.Interaction]::MsgBox("Use the row selector at the left to select one or multiple rows firt.`n(Press control for multiple selection)`nThen click install button again.", [Microsoft.VisualBasic.MsgBoxStyle]::OkOnly, "Information")
    }
    else {
        $message = "Are you sure you want to install these items? :`n"

        foreach ($row in $selectedRows) {
            $folderValue = $row.Cells[0].Value
            $message += "`n$folderValue "
            Write-Host "Selected Row: $folderValue, $sourceValue, $emuFolderValue, $romFolderValue"
        }

        $result = [Microsoft.VisualBasic.Interaction]::MsgBox($message, [Microsoft.VisualBasic.MsgBoxStyle]::YesNo, "Confirmation")
        if ($result -eq [Microsoft.VisualBasic.MsgBoxResult]::Yes) {
            foreach ($row in $selectedRows) {
                $folderValue = $row.Cells[0].Value
                $sourceValue = $row.Cells[1].Value
                $emuFolderValue = $row.Cells[2].Value
                $romFolderValue = $row.Cells[3].Value

                $sourcePath = "G:\App\PackageManager\data\$sourceValue\$folderValue\*"
                $destinationPath = "G:\"
        
                Copy-Item -Path $sourcePath -Destination $destinationPath -Recurse -Force
                Write-Host "******************** copying `"$sourcePath`" content to :`n$destinationPath"
            }
            & $RefreshItems
        }
    }
}

# Function to handle "pouet" button click event
$AutoInstallButton_Click = {

    $message = "Are you sure you want to install these items? :`n"

  
    foreach ($row in $dataGridView.Rows) {

        if ($row.DefaultCellStyle.BackColor -eq "Orange") {
            $folderValue = $row.Cells[0].Value
            $message += "`n$folderValue "
            Write-Host "Selected Row: $folderValue, $sourceValue, $emuFolderValue, $romFolderValue"
        }
    }

    $result = [Microsoft.VisualBasic.Interaction]::MsgBox($message, [Microsoft.VisualBasic.MsgBoxStyle]::YesNo, "Confirmation")
    if ($result -eq [Microsoft.VisualBasic.MsgBoxResult]::Yes) {
        foreach ($row in $dataGridView.Rows) {
            if ($row.DefaultCellStyle.BackColor -eq "Orange") {
                $folderValue = $row.Cells[0].Value
                $sourceValue = $row.Cells[1].Value
                $emuFolderValue = $row.Cells[2].Value
                $romFolderValue = $row.Cells[3].Value

                $sourcePath = "G:\App\PackageManager\data\$sourceValue\$folderValue\*"
                $destinationPath = "G:\"
        
                Copy-Item -Path $sourcePath -Destination $destinationPath -Recurse -Force
                Write-Host "******************** copying `"$sourcePath`" content to :`n$destinationPath"
            }
        }
        & $RefreshItems
    }
}



$UninstallButton_Click = {
    $selectedRows = $dataGridView.SelectedRows
    if ($selectedRows.Count -eq 0) {
        Write-Host "No rows selected."
        [Microsoft.VisualBasic.Interaction]::MsgBox("Use the row selector at the left to select one or multiple rows firt.`n(Press control for multiple selection)`nThen click uninstall button again.", [Microsoft.VisualBasic.MsgBoxStyle]::OkOnly, "Information")
    }
    else {
        $message = "Are you sure you want to uninstall these items? :`n"

        foreach ($row in $selectedRows) {
            $folderValue = $row.Cells[0].Value
            $message += "`n$folderValue "
            Write-Host "Selected Row: $folderValue, $sourceValue, $emuFolderValue, $romFolderValue"
        }
        if (($sourceValue -eq "Emu") -or ($sourceValue -eq "RApp")) { 
            $message += "`n`n(Your roms will not be deleted)" 
        }
        
        $result = [Microsoft.VisualBasic.Interaction]::MsgBox($message, [Microsoft.VisualBasic.MsgBoxStyle]::YesNo, "Confirmation")
        if ($result -eq [Microsoft.VisualBasic.MsgBoxResult]::Yes) {
            foreach ($row in $selectedRows) {
                $folderValue = $row.Cells[0].Value
                $sourceValue = $row.Cells[1].Value
                $emuFolderValue = $row.Cells[2].Value
                $romFolderValue = $row.Cells[3].Value

                $sourcePath = "G:\$sourceValue\$emuFolderValue"
        
                Remove-Item -Path $sourcePath  -Recurse -Force
                Write-Host "******************** Removing `"$sourcePath`""
            }
            & $RefreshItems
        }
    }
}

$RefreshItems = {
    $global:rowCountWithoutColor = 0
    $global:rowCountGreen = 0
    $global:rowCountOrange = 0
    $dataGridView.Rows.Clear()

    $selectedSource = $dropDown.SelectedItem.ToString()
    Write-Host "Selected source : $selectedSource"
    
    switch ($selectedSource) {
        "All" {
            FillTable -dataGridView $dataGridView -PackType "Emu"
            FillTable -dataGridView $dataGridView -PackType "RApp"
            FillTable -dataGridView $dataGridView -PackType "App"
        }
        "Emu" {
            FillTable -dataGridView $dataGridView -PackType "Emu"
        }
        "RApp" {
            FillTable -dataGridView $dataGridView -PackType "RApp"
        }
        "App" {
            FillTable -dataGridView $dataGridView -PackType "App"
        }
    }
}

# Create the form and controls
$form = New-Object System.Windows.Forms.Form
$form.Text = "Folder List"
$form.Size = New-Object System.Drawing.Size(615, 800)
$form.StartPosition = "CenterScreen"



$dropDown = New-Object System.Windows.Forms.ComboBox
$dropDown.DropDownStyle = [System.Windows.Forms.ComboBoxStyle]::DropDownList
$dropDown.Items.AddRange(@("All", "Emu", "RApp", "App"))
$dropDown.SelectedIndex = 0
$dropDown.add_SelectedIndexChanged($RefreshItems)



$labelRowCount = New-Object System.Windows.Forms.Label
$labelRowCount.Text = "Rows without color: 0, Rows in green: 0, Rows in orange: 0"
$labelRowCount.AutoSize = $true
$labelRowCount.Anchor = [System.Windows.Forms.AnchorStyles]::Top -bor [System.Windows.Forms.AnchorStyles]::Right



$dataGridView = New-Object System.Windows.Forms.DataGridView
$dataGridView.Dock = [System.Windows.Forms.DockStyle]::Fill
# $dataGridView.Size = New-Object System.Drawing.Size(580, 200)
# $dataGridView.RowHeadersVisible = $false
$dataGridView.RowHeadersWidth = 22
$dataGridView.AllowUserToAddRows = $false
$dataGridView.AllowUserToResizeRows = $false
$dataGridView.ReadOnly = $true
$dataGridView.AutoSizeColumnsMode = [System.Windows.Forms.DataGridViewAutoSizeColumnsMode]::AllCells # Automatically resize columns based on content
$dataGridView.Add_CellDoubleClick($DataGrid_CellDoubleClick) # Attach event handlers

$folderColumn = New-Object System.Windows.Forms.DataGridViewColumn
$folderColumn.HeaderText = "Folder"
$folderColumn.Name = "Folder"
$folderColumn.SortMode = [System.Windows.Forms.DataGridViewColumnSortMode]::Automatic
# $folderColumn.ReadOnly = $true
$dataGridView.Columns.Add($folderColumn)

$sourceColumn = New-Object System.Windows.Forms.DataGridViewColumn
$sourceColumn.HeaderText = "Source"
$sourceColumn.Name = "Source"
$sourceColumn.ReadOnly = $true
$dataGridView.Columns.Add($sourceColumn)

$EmufolderColumn = New-Object System.Windows.Forms.DataGridViewColumn
$EmufolderColumn.HeaderText = "Emu folder"
$EmufolderColumn.Name = "EmuFolder"
$EmufolderColumn.ReadOnly = $true
$dataGridView.Columns.Add($EmufolderColumn)

$romfolderColumn = New-Object System.Windows.Forms.DataGridViewColumn
$romfolderColumn.HeaderText = "Rom folder"
$romfolderColumn.Name = "RomFolder"
$romfolderColumn.ReadOnly = $true
$dataGridView.Columns.Add($romfolderColumn)

# Cr�ation du bouton "InstallButton"
$InstallButton = New-Object System.Windows.Forms.Button
$InstallButton.Text = "Install"
$InstallButton.Anchor = [System.Windows.Forms.AnchorStyles]::Bottom -bor [System.Windows.Forms.AnchorStyles]::Right
$InstallButton.add_Click($InstallButton_Click)

$AutoInstallButton = New-Object System.Windows.Forms.Button
$AutoInstallButton.Text = "Auto-Install"
$AutoInstallButton.Anchor = [System.Windows.Forms.AnchorStyles]::Bottom -bor [System.Windows.Forms.AnchorStyles]::Right
$AutoInstallButton.add_Click($AutoInstallButton_Click)


$UninstallButton = New-Object System.Windows.Forms.Button
$UninstallButton.Text = "Uninstall"
$UninstallButton.Anchor = [System.Windows.Forms.AnchorStyles]::Bottom -bor [System.Windows.Forms.AnchorStyles]::Right
$UninstallButton.add_Click($UninstallButton_Click)



# Add TextBox for filtering
$textBoxFilter = New-Object System.Windows.Forms.TextBox
$textBoxFilter.Anchor = [System.Windows.Forms.AnchorStyles]::Top -bor [System.Windows.Forms.AnchorStyles]::Left


# Attach event handler for filtering
$textBoxFilter.add_TextChanged({
        $filter = $textBoxFilter.Text.Trim()

        foreach ($row in $dataGridView.Rows) {
            $row.Visible = $row.Cells[0].Value -like "*$filter*" -or
            $row.Cells[1].Value -like "*$filter*" -or
            $row.Cells[2].Value -like "*$filter*" -or
            $row.Cells[3].Value -like "*$filter*"
        }
    })

$tooltip = New-Object System.Windows.Forms.ToolTip
$tooltip.SetToolTip($InstallButton, "This will install all the selected rows.`nUse the row selector at the left to select one or multiple rows firt.`n(Press control for multiple selection)`nThen click install button.")
$tooltip.SetToolTip($AutoInstallButton, "This will install all the emulators where roms are already present (orange lines).")
$tooltip.SetToolTip($UninstallButton, "This will uninstall all the selected rows.`nUse the row selector at the left to select one or multiple rows firt.`n(Press control for multiple selection)`nThen click uninstall button.")
$tooltip.SetToolTip($dropDown, "Select the type of items here.")
$tooltip.SetToolTip($textBoxFilter, "This is a filter field for all the elements of the table below.")

    


$dataGridViewContainer = New-Object System.Windows.Forms.Panel
$dataGridViewContainer.Dock = [System.Windows.Forms.DockStyle]::Fill
$dataGridViewContainer.Dock = 'Fill'

$tableLayoutPanel = New-Object System.Windows.Forms.TableLayoutPanel
$tableLayoutPanel.Dock = [System.Windows.Forms.DockStyle]::Fill

$dataGridViewContainer.Controls.Add($dataGridView)
# $tableLayoutPanel.Controls.Add($dataGridView,3)
$tableLayoutPanel.Controls.Add($textBoxFilter, 0, 1)
$tableLayoutPanel.Controls.Add($dropDown, 0, 0)
$tableLayoutPanel.Controls.Add($labelRowCount, 1, 0)
# $tableLayoutPanel.Controls.Add($dataGridViewContainer, 0, 3)
$tableLayoutPanel.Controls.Add($InstallButton, 2, 0)
$tableLayoutPanel.Controls.Add($UninstallButton, 2, 2)
$tableLayoutPanel.Controls.Add($AutoInstallButton, 2, 1)
# $form.Controls.Add($InstallButton)
# $form.Controls.Add($UninstallButton)

# $dataGridViewContainer.ColumnSpan = $tableLayoutPanel.ColumnCount
$tableLayoutPanel.Controls.Add($dataGridView)
$tableLayoutPanel.SetColumnSpan($dataGridView, 3) 
$tableLayoutPanel.BorderStyle = [System.Windows.Forms.BorderStyle]::FixedSingle

$form.Controls.Add($tableLayoutPanel)


# Initial population
# FillTable -dataGridView $dataGridView -PackType "Emu"
# FillTable -dataGridView $dataGridView -PackType "RApp"
# FillTable -dataGridView $dataGridView -PackType "App"
& $RefreshItems

[void]$form.ShowDialog()
