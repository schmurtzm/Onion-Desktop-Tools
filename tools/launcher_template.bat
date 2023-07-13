::[Bat To Exe Converter]
::
::YAwzoRdxOk+EWAjk
::fBw5plQjdCyDJGyX8VAjFDpYSRyLL1eeCaIS5Of66/m7j0QEW+1/VYbV04ixIfAD+XnbWpgk2XQar8ICCBRPbVKCYBwgqGJOs3a5JcKPjwDvQ0eHqEIzFAU=
::YAwzuBVtJxjWCl3EqQJgSA==
::ZR4luwNxJguZRRnk
::Yhs/ulQjdF+5
::cxAkpRVqdFKZSDk=
::cBs/ulQjdF+5
::ZR41oxFsdFKZSDk=
::eBoioBt6dFKZSDk=
::cRo6pxp7LAbNWATEpSI=
::egkzugNsPRvcWATEpSI=
::dAsiuh18IRvcCxnZtBJQ
::cRYluBh/LU+EWAnk
::YxY4rhs+aU+JeA==
::cxY6rQJ7JhzQF1fEqQJQ
::ZQ05rAF9IBncCkqN+0xwdVs0
::ZQ05rAF9IAHYFVzEqQJQ
::eg0/rx1wNQPfEVWB+kM9LVsJDGQ=
::fBEirQZwNQPfEVWB+kM9LVsJDGQ=
::cRolqwZ3JBvQF1fEqQJQ
::dhA7uBVwLU+EWDk=
::YQ03rBFzNR3SWATElA==
::dhAmsQZ3MwfNWATElA==
::ZQ0/vhVqMQ3MEVWAtB9wSA==
::Zg8zqx1/OA3MEVWAtB9wSA==
::dhA7pRFwIByZRRnk
::Zh4grVQjdCyDJGyX8VAjFDpYSRyLL1eeCaIS5Of66/m7j0QEW+1/VYbV04ixIfAD+XnbWpgk2XQar8ICCBRPbVKCYBwgqGJOs3a5GMmVvAGhbk2a7V8/CyVAiGzcn2t2IORhjssg3C6t80H60aAI1Bg=
::YB416Ek+ZW8=
::
::
::978f952a14a936cc963da21a135fa983
@echo off
cd /d %~dp0
echo "%0"
echo "%1"
if "%1"=="HighDPI" (
    powershell -ExecutionPolicy Bypass -File menu.ps1 -HighDPI "1"
) else (
    powershell -ExecutionPolicy Bypass -File menu.ps1
)