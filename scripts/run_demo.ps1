# run_demo.ps1 - run the full pipeline on one audio file and print the result
# Usage: .\scripts\run_demo.ps1 <path-to-audio-file>
param(
    [Parameter(Mandatory=$true)]
    [string]$AudioFile,
    [int]$NumSpeakers = 2,
    [switch]$NoLLM
)

Set-Location $PSScriptRoot\..

if (-not (Test-Path .venv\Scripts\Activate.ps1)) {
    Write-Host "Virtual environment not found. Run .\scripts\setup.ps1 first." -ForegroundColor Red
    exit 1
}
& .venv\Scripts\Activate.ps1

if (-not (Test-Path $AudioFile)) {
    Write-Host "File not found: $AudioFile" -ForegroundColor Red
    exit 1
}

$useLLM = if ($NoLLM) { "False" } else { "True" }

Write-Host "Running DealSense pipeline on: $AudioFile" -ForegroundColor Cyan
Write-Host "Speakers: $NumSpeakers | LLM: $useLLM`n" -ForegroundColor Cyan

python -c @"
from pathlib import Path
from src.pipeline import run

result = run(
    Path(r'$AudioFile'),
    num_speakers=$NumSpeakers,
    use_llm=$useLLM,
)
p = result.prediction
print('=' * 60)
print(f'Meeting ID : {result.meeting_id}')
print(f'Turns      : {len(result.transcript.turns)}')
print(f'Verdict    : {p.verdict if p else "n/a"}')
print(f'Probability: {round(p.probability * 100, 1) if p else "n/a"}%')
print('=' * 60)
if p:
    print(p.summary)
    if p.positives:
        print('\nPositives:')
        for item in p.positives:
            print(f'  + {item}')
    if p.risks:
        print('\nRisks:')
        for item in p.risks:
            print(f'  - {item}')
print('\nTranscript:')
print(result.transcript.as_text())
"@
