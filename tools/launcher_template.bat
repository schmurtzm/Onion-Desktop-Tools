::[Bat To Exe Converter]
::
::YAwzoRdxOk+EWAjk
::fBw5plQjdCyDJGyX8VAjFDpYSRyLL1eeCaIS5Of66/m7j0QEW+1/VYbV04ixBOUF1mrqfJkjm15fi8AYAwsVSh2kYhwIvWFNune5JcKPjwDvQ0eHqEIzFAU=
::YAwzuBVtJxjWCl3EqQJgSA==
::ZR4luwNxJguZRRnk
::Yhs/ulQjdF+5
::cxAkpRVqdFKZSTk=
::cBs/ulQjdF+5
::ZR41oxFsdFKZSDk=
::eBoioBt6dFKZSDk=
::cRo6pxp7LAbNWATEpSI=
::egkzugNsPRvcWATEpSI=
::dAsiuh18IRvcCxnZtBJQ
::cRYluBh/LU+EWAnk
::YxY4rhs+aU+IeA==
::cxY6rQJ7JhzQF1fEqQJQ
::ZQ05rAF9IBncCkqN+0xwdVs0
::ZQ05rAF9IAHYFVzEqQJQ
::eg0/rx1wNQPfEVWB+kM9LVsJDGQ=
::fBEirQZwNQPfEVWB+kM9LVsJDGQ=
::cRolqwZ3JBvQF1fEqQIfJhJbQkSmOXixEroMqNz04OaU4mEcQew8cIrJug==
::dhA7uBVwLU+EWHaK/U0+aC59LA==
::YQ03rBFzNR3SWATElA==
::dhAmsQZ3MwfNWATElA==
::ZQ0/vhVqMQ3MEVWAtB9wSA==
::Zg8zqx1/OA3MEVWAtB9wSA==
::dhA7pRFwIByZRRnk
::Zh4grVQjdCyDJGyX8VAjFDpYSRyLL1eeCaIS5Of66/m7j0QEW+1/VYbV04ixBOUF1mrqfJkjm15fi8AYAwsVSh2kYhwIhmBLuWrFE8KPuBvuWgi96UQ8CCtxn2aw
::YB416Ek+ZW8=
::
::
::978f952a14a936cc963da21a135fa983
@echo off
cd /d %~dp0
md backups 2> NUL
md downloads\ODT_updates 2> NUL
copy ODT_update.ps1 ODT_update_temporary.ps1 /Y >NUL
powershell -ExecutionPolicy Bypass -File ODT_update_temporary.ps1