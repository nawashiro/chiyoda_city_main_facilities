@echo off
setlocal enabledelayedexpansion

echo ========================================================================
echo �o���A�t���[�{�݃f�[�^�����o�b�`
echo ========================================================================
echo.

REM ���z�����A�N�e�B�x�[�g
echo ���z�����A�N�e�B�x�[�g���Ă��܂�...
call venv\Scripts\activate.bat
if %ERRORLEVEL% neq 0 (
    echo ���z���̃A�N�e�B�x�[�g�Ɏ��s���܂����B
    echo venv �f�B���N�g�������݂��邩�m�F���Ă��������B
    exit /b 1
)
echo ���z���̃A�N�e�B�x�[�g���������܂����B
echo.

REM �{�݂ƒ◯���̋����`�F�b�N�X�N���v�g���s
echo �{�݂ƒ◯���̋����`�F�b�N�X�N���v�g�����s���Ă��܂�...
python src/facilities_check.py
if %ERRORLEVEL% neq 0 (
    echo �����`�F�b�N�X�N���v�g�̎��s�Ɏ��s���܂����B
    echo �X�N���v�g�̃G���[���m�F���Ă��������B
    exit /b 2
)
echo �����`�F�b�N�X�N���v�g�̎��s���������܂����B
echo.

REM JSON���k�c�[�����s
echo �eJSON�t�H���_�����k�������Ă��܂�...

REM kazaguruma_json�t�H���_������
if exist kazaguruma_json (
    echo kazaguruma_json�t�H���_��������...
    python src/json_minifier.py kazaguruma_json
    if %ERRORLEVEL% neq 0 (
        echo kazaguruma_json�t�H���_�̈��k�����Ɏ��s���܂����B
        echo �ڍׂȃG���[���b�Z�[�W���m�F���Ă��������B
    ) else (
        echo kazaguruma_json�t�H���_�̈��k�������������܂����B
    )
    echo.
) else (
    echo kazaguruma_json�t�H���_��������܂���B�������X�L�b�v���܂��B
    echo.
)

REM json�t�H���_������
if exist json (
    echo json�t�H���_��������...
    python src/json_minifier.py json
    if %ERRORLEVEL% neq 0 (
        echo json�t�H���_�̈��k�����Ɏ��s���܂����B
        echo �ڍׂȃG���[���b�Z�[�W���m�F���Ă��������B
    ) else (
        echo json�t�H���_�̈��k�������������܂����B
    )
    echo.
) else (
    echo json�t�H���_��������܂���B�������X�L�b�v���܂��B
    echo.
)

REM ��������
echo ========================================================================
echo �S�Ă̏������������܂����B
echo ========================================================================

REM ���z�����A�N�e�B�u��
call deactivate
pause 