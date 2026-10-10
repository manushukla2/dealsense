# DealSense
## Product Requirements Document & Product Blueprint

> **Version:** 1.0  
> **Status:** MVP implemented locally; deployment and product hardening in progress  
> **Prepared:** 10 October 2026  
> **Product type:** AI-powered sales-meeting intelligence  
> **Primary audience:** Sales representatives, sales managers, founders, and revenue teams  
> **Working repository:** `https://github.com/manushukla2/dealsense`

---

## 1. Executive Summary

**DealSense turns sales-meeting audio into evidence-backed deal intelligence.**

A user uploads a meeting recording, records a conversation in the browser, or submits a transcript. DealSense transcribes the conversation, identifies who said what, examines the conversation exchange by exchange, and produces:

- A **deal-outcome estimate** expressed as a percentage.
- An overall verdict, such as *Leaning positive*, *Uncertain*, or *At risk*.
- A clear explanation of important moments in the conversation.
- Positive buying signals and risks.
- A readable, timestamped transcript with speaker labels.
- A visual representation of the analysis pipeline.
- A dashboard, analysis history, and settings experience as the product evolves.

The product's differentiator is not simply transcription or sentiment classification. It is the **traceable connection between what the buyer said, how the seller responded, what the buyer said next, and what those exchanges may imply about the deal**.

### Product principle

> Every prediction should be explainable, every explanation should point to conversation evidence, and every percentage should communicate its limitations honestly.

**Important limitation:** the current end-to-end demo uses a heuristic scoring method and has not been calibrated against a representative dataset of real won/lost sales meetings. Until that validation exists, the percentage is an estimate—not a reliable, production-grade probability.

---

## 2. Product Vision

### Vision statement

Help sales teams understand the health of a deal earlier by turning sales conversations into structured, explainable signals that support better follow-up decisions.

### The problem

Sales conversations contain useful signals, but those signals are easy to miss or interpret inconsistently:

- A buyer may object to price but remain interested.
- A request for technical documentation may indicate serious evaluation—or routine information gathering.
- Mentioning a CFO, budget, deadline, competitor, or current supplier can change the interpretation of a conversation.
- A positive tone alone does not mean a deal will close.
- Managers may not have time to listen to every recording in full.

A transcript alone does not solve this. Users need a structured interpretation tied to specific statements and responses.

### Proposed value

DealSense aims to help a user answer five questions:

1. **What happened in the meeting?**
2. **What did the buyer's responses suggest?**
3. **Which moments strengthened or weakened the deal?**
4. **What is the current estimated chance of a positive outcome?**
5. **What should the salesperson investigate or do next?**

The fifth question is a proposed product extension; recommendations must be evidence-based and should not be represented as already implemented unless verified in the codebase.

---

## 3. Target Users & Jobs to Be Done

### Primary personas

| Persona | Need | DealSense value |
|---|---|---|
| Sales representative | Understand whether a prospect is genuinely interested and prepare the next follow-up | A quick readout of buying signals, objections, and agreed next steps |
| Sales manager | Review calls consistently across a team | A structured summary and a common framework for discussing deal health |
| Founder / small-business owner | Make sense of important customer calls without a dedicated sales-operations team | Meeting intelligence in a simple upload-and-review workflow |
| Revenue operations / analyst | Explore patterns across conversations and outcomes | A potential foundation for historical analysis once real outcome data is available |

### Jobs to be done

- “After a sales call, help me understand the buyer's actual level of interest.”
- “Show me the exact exchanges that influenced the assessment.”
- “Help me distinguish a genuine buying signal from polite conversation.”
- “Give me a concise summary without making me replay the entire recording.”
- “Let me revisit prior analyses and compare the reasoning.”

---

## 4. Product Scope

### MVP scope

The MVP should focus on a dependable single-meeting workflow.

- Upload an audio file for analysis.
- Record audio using the browser microphone.
- Automatically begin transcription after recording stops.
- Submit transcript text directly, where supported by the API.
- Produce speaker-labelled, timestamped transcript output.
- Analyse conversation exchanges for sentiment and intent signals.
- Produce an overall verdict, estimated percentage, summary, positives, and risks.
- Display the analysis in a polished web interface.
- Show the pipeline stages and their connections.
- Provide clear loading, error, and completion states.
- Run the frontend and backend locally.
- Prepare a deployable backend and configurable frontend API URL.

### Planned product areas

The conversation explicitly identifies three product areas to build: **Dashboard, History, and Settings**. Their final behaviour and persistence rules still need to be defined and tested.

| Area | Intended role | MVP acceptance direction |
|---|---|---|
| Dashboard | Main workspace to start an analysis and view the result | User can start an analysis and understand the result without confusion |
| History | Return to earlier meeting analyses | Saved records can be listed and reopened; requires durable storage |
| Settings | Configure user-facing preferences and application behaviour | Only show settings that are actually supported; avoid decorative, non-functional controls |

### Not in confirmed scope

The source conversations describe **audio recording and audio-file analysis**, not video recording or video-call capture. Video ingestion should be treated as a separate future decision. The project should not claim to record video unless that capability is deliberately designed, implemented, permissioned, and tested.

Other items not confirmed as implemented:
- CRM integrations.
- Team accounts and role-based access.
- Real-time live transcription while a person is speaking.
- Automated email or CRM follow-up.
- Production-grade deal probability calibrated on real sales outcomes.
- Multi-tenant analytics and billing.

---

## 5. Core User Journey

### Journey A — Upload a meeting recording

1. User opens DealSense.
2. User selects **Upload audio**.
3. User chooses a supported recording.
4. The interface validates the file and shows its name and upload/analysis state.
5. Backend receives the file and runs the pipeline.
6. UI shows progress without inventing completion or model activity.
7. User receives the transcript, verdict, estimated probability, reasoning, positives, and risks.
8. User reviews the transcript and evidence behind the result.
9. User can return to the dashboard or, once persistence is implemented, open the saved analysis in History.

### Journey B — Record a meeting or voice sample

1. User opens the **Record** tab.
2. Browser requests microphone permission.
3. User starts recording and sees a timer and clear recording state.
4. User stops recording.
5. The recording is automatically submitted for transcription.
6. Transcript text appears when the transcription request completes.
7. User can proceed to deal analysis.
8. The UI shows each pipeline stage and its current status.
9. Errors explain what failed and how to recover.

**Terminology note:** the existing implementation described in the conversation automatically transcribes after recording stops. That is not the same as live, streaming transcription while recording is still in progress. True live transcription would require incremental audio submission and partial transcript updates.

### Journey C — Analyse pasted text

1. User chooses the transcript-text input mode.
2. User pastes or types a transcript.
3. User submits it for analysis.
4. DealSense returns a prediction and evidence-based reasoning.
5. The result clearly indicates that it was based on text rather than original audio, so speaker diarization and acoustic evidence are not implied.

---

## 6. Functional Requirements

Priority definitions: **P0 = essential for MVP**, **P1 = important next**, **P2 = later enhancement**.

### 6.1 Input and ingestion

| ID | Priority | Requirement | Acceptance criteria |
|---|---|---|---|
| ING-01 | P0 | Accept supported audio uploads | Valid audio can be submitted; invalid files receive a clear error |
| ING-02 | P0 | Record audio through the browser | User can grant microphone access, start, stop, and review the recording state |
| ING-03 | P0 | Auto-transcribe after recording stops | Stopping a recording triggers transcription without requiring a second “Transcribe” click |
| ING-04 | P0 | Support a transcript text path | Text can be sent to the relevant backend endpoint, if available |
| ING-05 | P0 | Validate size and type | The user receives a helpful message for unsupported or oversized files |
| ING-06 | P1 | Show recording duration and retry controls | User can discard and re-record before analysis |
| ING-07 | P1 | Handle long audio safely | Long recordings are chunked or rejected with a clear limit; requests do not fail silently |

### 6.2 Transcription and speaker attribution

| ID | Priority | Requirement | Acceptance criteria |
|---|---|---|---|
| TRN-01 | P0 | Convert audio to text | Transcript is returned through the transcription pipeline |
| TRN-02 | P0 | Preserve timestamps where available | Transcript turns or segments include readable timestamps |
| TRN-03 | P0 | Attribute speakers where supported | Turns display speaker labels such as `REP` and `CLIENT` |
| TRN-04 | P0 | Display transcript text | Transcript is readable and can be reviewed after analysis |
| TRN-05 | P1 | Surface transcription uncertainty | The interface does not present uncertain speech as guaranteed fact |
| TRN-06 | P1 | Support transcript correction | A user can correct a transcript before rerunning analysis, if product design permits |

The system must not imply that speaker labels are always correct. Diarization identifies speaker clusters; mapping a cluster to “REP” or “CLIENT” can require configuration or user confirmation.

### 6.3 Exchange-level intent and evidence

| ID | Priority | Requirement | Acceptance criteria |
|---|---|---|---|
| ANA-01 | P0 | Interpret conversation exchanges | The result explains meaningful statement-response sequences |
| ANA-02 | P0 | Identify positive and negative signals | Signals are shown with concise explanations |
| ANA-03 | P0 | Produce an overall assessment | A readable verdict and summary are displayed |
| ANA-04 | P0 | Return an estimated percentage | Percentage is derived from the scoring layer and its limitations are disclosed |
| ANA-05 | P0 | Show positives and risks | Each list is shown only when there are relevant items |
| ANA-06 | P0 | Ground reasoning in the transcript | Explanations should reference actual transcript content, not invented quotes |
| ANA-07 | P1 | Link evidence to timestamps | Selecting a reasoning item can take the user to the relevant transcript moment |
| ANA-08 | P1 | Show neutral or ambiguous evidence | The model can express uncertainty instead of forcing every exchange into positive/negative |
| ANA-09 | P1 | Recommend follow-up actions | Any suggested action must be clearly distinguished from observed evidence |

### 6.4 User interface

| ID | Priority | Requirement | Acceptance criteria |
|---|---|---|---|
| UI-01 | P0 | Classy, professional visual design | Consistent spacing, typography, hierarchy, colour, and responsive layout |
| UI-02 | P0 | Clear analysis states | Loading, success, empty, and error states are visually distinct |
| UI-03 | P0 | Result card | Verdict, probability, summary, positives, risks, and transcript are legible |
| UI-04 | P0 | Visual pipeline | Nodes and connections show the actual analysis stages in order |
| UI-05 | P1 | Dashboard | Main workspace brings input and latest analysis together |
| UI-06 | P1 | History | Past analyses can be listed and reopened after storage is implemented |
| UI-07 | P1 | Settings | Only functional, supported settings are displayed |
| UI-08 | P1 | Export/share report | Export should preserve the verdict, percentage, evidence, and uncertainty disclaimer |
| UI-09 | P2 | Compare multiple meetings | Requires persisted meeting data and a defined comparison method |

---

## 7. Product Experience & Visual Direction

### Design positioning

**Classy, analytical, trustworthy, and calm.** The interface should feel like a premium revenue-intelligence workspace—not a flashy demo or a generic upload form.

### Visual direction from the implementation conversation

- Dark interface with a near-black base.
- Restrained blue-to-violet accent gradient.
- High-contrast headings and muted secondary text.
- Subtle borders and translucent surfaces.
- Rounded cards with consistent spacing.
- Small, purposeful animations for progress and state changes.
- Charts and pipeline visuals that explain the product rather than decorate it.

Suggested design tokens (proposed, not verified as a final design system):

| Token | Suggested value | Usage |
|---|---|---|
| Background | `#0A0A0F` | App canvas |
| Surface | `#11131B` | Cards and panels |
| Primary accent | `#3B82F6` | Primary actions and active states |
| Secondary accent | `#8B5CF6` | Gradient and secondary emphasis |
| Main text | `#F8FAFC` | Headings and key values |
| Muted text | `#9CA3AF` | Supporting copy |
| Positive | Muted green | Positive signals; never the sole indicator |
| Caution | Muted amber | Uncertainty and watch-outs |
| Negative | Muted red | Risks and errors |

### Recommended page hierarchy

1. **Top navigation:** brand, Dashboard, History, Settings.
2. **Page heading:** “Understand the signals behind every sales conversation.”
3. **Input panel:** Upload audio / Record / Paste transcript.
4. **Pipeline visual:** clear node-to-node sequence and current status.
5. **Result overview:** verdict, probability, and concise summary.
6. **Evidence panel:** positives and risks with references to transcript moments.
7. **Transcript panel:** timestamps and speaker labels.
8. **Footer:** product name and accurate technology attribution.

### Chart recommendations

Charts should answer a question. Avoid adding graphs merely to make the page look sophisticated.

- **Probability gauge or progress bar:** the current estimated deal score.
- **Positive vs. risk signal summary:** count or weighted contribution only if the backend returns defensible values.
- **Conversation timeline:** plot evidence points against timestamps when timestamps and evidence labels are available.
- **Pipeline node graph:** visual explanation of processing stages, distinct from a statistical chart.
- **History trend chart:** only after saved meetings exist and the chart can explain its sample size and time range.

Do not fabricate chart values or imply that a heuristic score is a statistically validated probability.

---

## 8. Pipeline & Technical Architecture

### High-level flow

```text
Audio upload / Browser recording / Transcript text
                         |
                         v
              Input validation & ingestion
                         |
             +-----------+-----------+
             |                       |
             v                       v
       Audio preprocessing      Text validation
             |
             v
      Speech-to-text (Whisper API)
             |
             v
     Speaker diarization / alignment
             |
             v
      Timestamped speaker transcript
             |
             v
       Exchange segmentation
             |
             v
      Sentiment and intent signals
             |
             v
      Deal outcome scoring layer
             |
             v
      Evidence-based reasoning layer
             |
             v
       Structured prediction result
             |
             v
     Dashboard / Transcript / History
```

The text-input path can skip audio preprocessing, transcription, and diarization. It should not pretend those stages ran.

### Pipeline stages shown in the UI

The current frontend work describes these seven stages:

1. **Audio Ingestion** — receive and prepare audio.
2. **Transcription** — convert speech to text.
3. **Speaker Diarization** — identify speaker turns.
4. **Exchange Segmentation** — group statements and responses into exchanges.
5. **Sentiment Analysis** — classify conversation tone and related signals.
6. **Deal Scoring** — estimate deal outcome.
7. **Reasoning** — produce a plain-English explanation.

The visual pipeline should represent real backend state where possible. If progress is only simulated, it must not mislead users into believing the backend has confirmed that a stage completed.

### Technology stack

| Layer | Technology described in the conversations | Role / status |
|---|---|---|
| Language | Python 3.11 | Backend and ML pipeline |
| API | FastAPI + Uvicorn | Upload and prediction endpoints |
| Transcription | Groq-hosted Whisper (`whisper-large-v3` / `whisper-large-v3-turbo`) | Chosen as a free-tier API option for the current build; limits may change |
| Audio processing | `ffmpeg`, `pydub`, `soundfile`, `numpy` | Conversion, chunking, and preprocessing where needed |
| Speaker diarization | `pyannote.audio` | Speaker-turn detection; requires correct configuration and compatible access |
| NLP | Hugging Face Transformers; RoBERTa sentiment model | Per-exchange sentiment/intent signals |
| Scoring | Current heuristic scorer | MVP estimate; not calibrated on real sales outcomes |
| Reasoning | Optional LLM integration was discussed | Must be verified against current configuration and secrets |
| Frontend | React + Vite | Web application |
| Styling | Tailwind CSS via Vite plugin | UI styling |
| HTTP | Axios | Frontend API requests |
| Upload interaction | `react-dropzone` | Drag-and-drop file upload |
| Charts | Recharts was proposed | Use only for meaningful, data-backed charts |
| Pipeline graph | React Flow (`reactflow` package was proposed) | Node-and-edge pipeline visual |
| Report capture | `html2canvas` was installed in the conversation | Potential export/screenshot capability; behaviour must be verified |
| Configuration | `.env`, `VITE_API_URL` | Keep backend URLs configurable |
| Version control | Git + GitHub | Repository: `manushukla2/dealsense` |
| Deployment | Railway was being explored; Hugging Face Spaces Docker was rejected due to paid-tier limitation shown in the UI | Deployment choice remains unresolved in the conversation |
| Container | Dockerfile targeting port `7860` was drafted for Hugging Face Spaces | Reuse only if the chosen host supports the setup |

**Stack caveat:** this table consolidates technologies discussed across the two conversations. It is not a fresh code audit. Some packages were installed or proposed, but every listed component should be checked in the current repository before treating it as production-ready.

---

## 9. Backend API Contract

The conversation describes these endpoints in the README draft and frontend integration:

| Endpoint | Purpose | Expected input | Expected output |
|---|---|---|---|
| `POST /predict` | Analyse an audio file and estimate the deal outcome | Multipart audio file | Structured prediction, transcript, positives, risks, and summary |
| `POST /transcribe` | Transcribe an audio file without necessarily scoring the deal | Multipart audio file | Transcript text and, where available, segments/timestamps |
| `POST /predict-text` | Analyse a supplied transcript | JSON or text payload, depending on implementation | Structured prediction and reasoning |

**Implementation note:** confirm the actual request and response schemas in `src/api.py`, `src/schemas.py`, and the current pipeline before changing frontend code. The conversation contains iterations using both `src.api:app` and earlier `api.main:app` paths. The latest deployment instructions use `src.api:app`.

### Suggested result shape

This is a product-level contract proposal; align it with the actual Pydantic models before implementation.

```json
{
  "meeting_id": "uuid",
  "transcript": {
    "turns": [
      {
        "speaker": "CLIENT",
        "start": 8.0,
        "text": "Your pricing seems a bit high compared to what we use now."
      }
    ]
  },
  "prediction": {
    "verdict": "Leaning positive",
    "probability": 0.723,
    "summary": "The buyer showed interest but raised a pricing concern.",
    "positives": [
      "The buyer is taking the proposal to a decision-maker."
    ],
    "risks": [
      "The buyer objected to the price."
    ],
    "calibration_status": "not calibrated"
  }
}
```

Do not use this example as proof that every field currently exists. It is a target contract for a consistent frontend/backend integration.

---

## 10. ML & Data Strategy

### 10.1 Current approach

The successful local demo shown in the conversation processed a sample `dialogue.wav` and returned:

- **Turns:** 4
- **Verdict:** Leaning positive
- **Estimated probability:** 72.3%
- **Positive signals:** positive tone, later-meeting trend, decision-maker involvement, and a timeline
- **Risks:** price objection and mention of a competitor/current tool
- **Caveat:** heuristic score, limited evidence, not calibrated against real won/lost data

This is a useful end-to-end demonstration, not evidence of predictive accuracy.

### 10.2 Training-data reality

The conversations identify a critical data gap: there is no confirmed public dataset that directly provides a large, representative set of real B2B sales-meeting recordings paired with final won/lost outcomes.

Datasets discussed as useful proxies include:

| Dataset | Intended use | Limitation to respect |
|---|---|---|
| AMI Meeting Corpus | Real multi-speaker meeting audio and transcripts | General meetings, not sales outcome labels |
| MELD | Emotion/sentiment in multi-speaker dialogue | Fictional/acted dialogue; not B2B sales |
| DailyDialog | Dialogue emotion and intent-style experiments | Not sales calls; licence restrictions need review |
| Banking77 | Intent classification patterns | Banking customer-service intents, not deal outcomes |
| CLINC150 | General intent classification | Not sales-specific |
| MeetingBank / QMSum | Meeting understanding and summarisation | Does not directly provide sales win/loss labels |
| CraigslistBargains | Buyer/seller negotiation outcomes | Negotiation proxy, not enterprise sales |
| Language of Bargaining | Negotiation speech acts and outcomes | Access conditions and domain fit need review |
| IBM/Kaggle-style CRM win/loss datasets | Deal-level labels and structured features | Often lacks conversation transcripts |

Before commercial use, verify the exact dataset source, current licence, consent conditions, redistribution rules, and suitability. The original conversation flagged licence concerns for some datasets.

### 10.3 Recommended staged model plan

1. **Transcription first:** use the current Whisper API path and measure transcription quality on representative recordings.
2. **Speaker handling:** verify diarization quality and whether speaker-to-role mapping needs user confirmation.
3. **Exchange construction:** create reliable statement-response units with timestamps.
4. **Signal extraction:** start with transparent sentiment, intent, objection, urgency, budget, decision-maker, competitor, and next-step signals.
5. **Baseline scorer:** retain a transparent heuristic baseline while recording its limitations.
6. **Proxy-data experiments:** use negotiation datasets only for experiments, clearly documenting the domain mismatch.
7. **Collect labelled outcomes:** obtain consented meeting transcripts/recordings with reliable final outcomes and consistent definitions.
8. **Train and evaluate:** split data by customer/deal (not random transcript turns) to reduce leakage.
9. **Calibrate probabilities:** evaluate calibration on held-out, representative sales outcomes.
10. **Generate reasoning:** use an LLM or template-based layer to explain evidence already extracted by the system; do not allow it to invent supporting quotes.

### 10.4 Probability and trust

The product should distinguish:

- **Score:** the current model's output.
- **Probability:** a score shown to correspond to observed outcome frequency after appropriate calibration and validation.
- **Confidence/uncertainty:** how much evidence is available and how reliable the estimate is.

Until real-outcome calibration is completed, label the number **“estimated deal score”** or clearly state **“rough estimate; not calibrated”**. Avoid implying that 72% means exactly 72 out of 100 comparable deals will close.

### 10.5 Evaluation plan

| Layer | Metrics / checks |
|---|---|
| Transcription | Word error rate where reference transcripts exist; manual review of business terms, names, numbers, and accents |
| Diarization | Speaker attribution error and manual review of REP/CLIENT mapping |
| Intent/sentiment | Per-class precision, recall, F1, confusion matrix |
| Deal classification | ROC-AUC, precision/recall, PR-AUC where class imbalance warrants it |
| Probability calibration | Brier score, reliability diagram, calibration error |
| Reasoning | Evidence faithfulness, quote accuracy, usefulness ratings, contradiction checks |
| Product | Successful analysis rate, time to result, upload failure rate, repeat usage, user-reported usefulness |

No performance metric should be advertised until it has been measured on an appropriately separated evaluation set.

---

## 11. Dashboard, History & Settings — Product Definition

These areas were requested, but their full implementation is not confirmed in the conversation.

### Dashboard

**Purpose:** start a new analysis and understand the latest result.

Recommended components:
- Main call to action: Upload audio, Record, or Paste transcript.
- Recent analysis card(s), only if data persistence exists.
- Result overview: verdict, score, positives, risks.
- Pipeline graph showing the current run.
- Empty state for a first-time user.
- Error state with a retry path.

### History

**Purpose:** make meeting analysis useful beyond a one-off demo.

Recommended list fields:
- Meeting title or source filename.
- Analysis date and duration, where known.
- Verdict and estimated score.
- Processing status.
- Open/view action.
- Delete action with confirmation, if deletion is supported.

**Dependency:** a real history page needs a database or another durable persistence mechanism. Browser-only state will disappear on refresh and should not be described as persistent history.

### Settings

Keep this minimal until actual requirements are agreed. Potential future settings:
- Default speaker labels / role mapping.
- Preferred language, if supported.
- Data retention and deletion controls.
- API or model configuration for an administrator, never exposed as client-side secrets.
- Export preferences.
- Privacy notice and consent information.

Do not show API keys in the browser. Frontend environment variables prefixed with `VITE_` are bundled into client-side code and must not contain secrets.

---

## 12. Security, Privacy & Responsible Use

Meeting recordings can contain confidential business information and personal data. Privacy must be designed into the product from the start.

### Minimum safeguards

- Obtain appropriate consent before recording or uploading meetings.
- Explain which services process the audio and where data may be sent.
- Do not upload confidential calls to third-party transcription services without checking their applicable terms and privacy controls.
- Store API keys only in backend environment variables or the host's secret manager.
- Keep `.env` and real credentials out of Git; the conversation shows `.env` is included in `.gitignore`.
- Avoid logging raw transcripts, recordings, or credentials by default.
- Define retention and deletion rules before adding persistent history.
- Restrict access to stored recordings and reports.
- Validate file types, sizes, and request limits.
- Use HTTPS in deployment.
- Treat model outputs as decision support, not a guarantee or a substitute for human judgement.

### Frontend source protection

A browser application cannot be made truly secret by disabling developer tools, minifying JavaScript, or obfuscating the bundle. Users can inspect code delivered to their browser. Keep proprietary logic, credentials, and sensitive scoring logic on the backend. Minification can reduce bundle size and casual readability, but it is not a security boundary.

### Bias and interpretation risks

Sentiment can be affected by accent, language, communication style, culture, and context. A price objection does not necessarily mean a deal is failing, and a polite positive response does not prove buying intent. The product should surface evidence and uncertainty rather than make categorical judgements about a buyer.

---

## 13. Deployment & Environment

### Confirmed development context

- Windows / PowerShell.
- Project directory used in the conversation: `C:\Users\manus\Documents\dealsense`.
- Python virtual environment: `.venv`.
- Frontend: `frontend/`, React + Vite.
- Local frontend URL observed: `http://localhost:5173/`.
- Local backend port: `8000`.
- GitHub repository referenced: `https://github.com/manushukla2/dealsense`.

### Environment configuration

The frontend was being updated to use a configurable API URL. The intended pattern is:

```env
VITE_API_URL=http://localhost:8000
```

In the frontend, use a central API helper and a fallback only for local development. For deployment, set `VITE_API_URL` to the deployed backend's HTTPS URL and rebuild the frontend.

Backend secrets such as the Groq API key belong in backend environment configuration—not in a `VITE_` variable and not in source control.

### Deployment status at the end of the conversation

- A Dockerfile and Hugging Face Spaces README were drafted for the FastAPI backend.
- The user saw that Docker Spaces required a paid tier in the interface they were using.
- Railway was then being explored, and the Railway dashboard was open.
- The last visible instruction was to create a new Railway project from the GitHub repository `manushukla2/dealsense`.
- **A successful public deployment was not confirmed in the provided conversations.**

### Deployment checklist

- [ ] Confirm the backend starts using `uvicorn src.api:app` in the selected host.
- [ ] Configure all required secrets in the host dashboard.
- [ ] Confirm the production start command and port binding.
- [ ] Configure CORS for the deployed frontend origin only.
- [ ] Confirm audio upload size and timeout behaviour.
- [ ] Add a health endpoint or verify the available health check.
- [ ] Set `VITE_API_URL` to the deployed backend URL and rebuild the frontend.
- [ ] Test `/transcribe`, `/predict`, and `/predict-text` against the actual schemas.
- [ ] Test microphone permissions and recording on HTTPS.
- [ ] Test a fresh deployment from the current GitHub commit.
- [ ] Document cold-start, free-tier, rate-limit, and uptime constraints.
- [ ] Verify no secrets or private recordings are committed.

---

## 14. Quality Assurance & Acceptance Tests

### Core test scenarios

| Test | Expected result |
|---|---|
| Valid audio upload | Request is accepted and analysis result is rendered |
| Unsupported file | Helpful validation error; backend does not crash |
| Empty or silent recording | Clear no-speech or low-evidence message |
| Browser microphone denied | Permission explanation and alternate upload path |
| Stop browser recording | Recording stops and transcription starts automatically |
| Transcription API unavailable | Clear error with retry path; no fake transcript |
| Backend unavailable | Frontend reports connectivity issue |
| Text-only transcript | Prediction works without claiming audio or diarization ran |
| Sparse transcript | Result explicitly communicates limited evidence |
| Ambiguous conversation | Output can express uncertainty rather than overstate confidence |
| Missing positives or risks | UI remains well-formed and does not render empty broken sections |
| Long transcript | Transcript panel remains usable and scrollable |
| API returns unexpected data | Error is handled safely; page does not crash |
| Refresh on History page | Saved records remain available only if persistence is implemented |
| Mobile / narrow viewport | Core workflow remains usable |
| Secrets audit | No API keys appear in frontend bundles, logs, or Git history |

### Definition of Done for the MVP

The MVP is ready for a controlled demo when:

- A user can upload a valid recording and receive a structured result.
- A user can record audio and have it transcribed automatically after stopping.
- Speaker-labelled transcript and analysis are displayed when the pipeline returns them.
- The result explains positive and negative signals using transcript evidence.
- The percentage is clearly labelled as uncalibrated while that remains true.
- Pipeline visuals reflect real status or are explicitly presented as illustrative.
- Loading, empty, and error states work.
- The frontend connects to the configured backend URL.
- Secrets are not exposed in the frontend or committed to the repository.
- A fresh local setup and a fresh deployment can be followed from documented instructions.

---

## 15. Roadmap

### Phase 0 — Stabilise the demo

- [x] Define the product concept and three-stage pipeline.
- [x] Build an initial backend pipeline.
- [x] Run a sample end-to-end demo producing transcript, verdict, positives, and risks.
- [x] Start the React + Vite frontend.
- [x] Add audio upload UI.
- [x] Add browser voice-recording component and automatic transcription after stop, as described in the conversation.
- [x] Push project changes to GitHub, according to the conversation.
- [ ] Verify current repository state and endpoint schemas.
- [ ] Fix remaining integration issues and document exact local run commands.

### Phase 1 — Complete the polished MVP

- [ ] Finalise the dashboard layout.
- [ ] Finalise the connected pipeline graph.
- [ ] Ensure the result page is evidence-led and responsive.
- [ ] Complete transcript input and validation.
- [ ] Standardise API response schemas.
- [ ] Add user-friendly empty, failure, and retry states.
- [ ] Add automated backend and frontend smoke tests.

### Phase 2 — Product foundations

- [ ] Implement durable meeting history.
- [ ] Define and implement supported settings.
- [ ] Add report export if still needed.
- [ ] Add deletion and data-retention behaviour.
- [ ] Add privacy and consent copy.
- [ ] Deploy backend and frontend to stable URLs.

### Phase 3 — Prediction quality

- [ ] Create a documented evaluation dataset.
- [ ] Define “won,” “lost,” and “not yet decided.”
- [ ] Build a baseline evaluation and calibration report.
- [ ] Validate reasoning faithfulness.
- [ ] Collect consented real-world outcomes.
- [ ] Train and validate a model on representative data.
- [ ] Replace proxy-only claims with measured, honest performance reporting.

### Phase 4 — Advanced intelligence

- [ ] Link evidence cards to transcript timestamps.
- [ ] Add cross-meeting trend views when enough data exists.
- [ ] Add follow-up suggestions based on agreed next steps.
- [ ] Explore CRM integration only after privacy, persistence, and model quality are sound.
- [ ] Consider video input only as a separately scoped feature.

---

## 16. Risks, Dependencies & Open Questions

| Risk / question | Why it matters | Recommended action |
|---|---|---|
| No representative won/lost meeting dataset | Final prediction cannot be validated reliably | Keep probability disclaimer; prioritise outcome-labelled data collection |
| Heuristic scorer may look more certain than it is | Users may over-trust a precise percentage | Label it as an estimate and display evidence limitations |
| Speaker-role mapping may be wrong | Reasoning can attribute intent to the wrong person | Allow role confirmation and evaluate diarization |
| Third-party transcription privacy | Meeting audio may contain sensitive commercial information | Review provider terms, consent, retention, and alternatives |
| Free-tier API limits can change | Demos can fail unexpectedly | Read provider limits from current account and handle rate limits |
| API endpoint drift | Frontend may call outdated routes or fields | Define one schema and central API client |
| Deployment host not final | Environment and port assumptions differ | Choose host, document start command, and run a clean deployment test |
| History needs persistence | A history UI without storage is misleading | Add a database or label the feature as not yet available |
| “Live transcription” ambiguity | Auto-transcription after stop is not streaming | Decide whether true streaming is a product requirement |
| Video recording ambiguity | Source conversations focus on audio | Keep video out of MVP unless explicitly approved and scoped |
| Browser bundle visibility | Client-side code can be inspected | Keep secrets and sensitive logic server-side |

### Decisions still needed

1. Is DealSense intended for a portfolio/demo, internal sales use, or a commercial product?
2. Should the MVP support audio only, or should video be considered later?
3. Is true live transcription during recording a must-have, or is auto-transcription after stopping sufficient for now?
4. Should meeting history be local-only initially, or persist in a database?
5. Which deployment host will be used for the backend and frontend?
6. Will the first version use only the heuristic scorer, or should an LLM reasoning layer be enabled?
7. What is the precise outcome definition: signed contract, closed-won CRM status, paid invoice, or another event?
8. How will users provide consent and how long should recordings be retained?

---

## 17. Product Analytics

Instrument only events needed to understand product quality, and avoid placing raw transcript text or audio content in analytics.

Suggested events:

- `analysis_started` — input type, file size bucket, not file contents.
- `transcription_completed` — duration and success/failure.
- `analysis_completed` — latency, input type, and model/scorer version.
- `analysis_failed` — stage and safe error category.
- `result_opened` — whether the result view loaded successfully.
- `transcript_corrected` — count or aggregate, not the transcript itself.
- `report_exported` — export format.
- `user_feedback_submitted` — rating and optional redacted feedback.

### Initial product metrics

- Successful analysis completion rate.
- Median time from submission to result.
- Transcription failure rate.
- Percentage of analyses with usable speaker labels.
- Percentage of results with evidence-backed reasoning.
- User-rated usefulness of the result.
- Repeat analysis usage.
- Calibration quality once verified outcomes become available.

Do not optimise solely for engagement or repeat usage; the product's success depends on trustworthy, useful analysis.

---

## 18. Documentation & Repository Expectations

Suggested documentation set:

```text
dealsense/
├── README.md                  # Product overview and quickstart
├── PRODUCT_REQUIREMENTS.md    # This product blueprint
├── .env.example               # Names of required variables, no secrets
├── requirements.txt           # Development dependencies
├── requirements-prod.txt      # Production dependencies, if maintained separately
├── Dockerfile                 # Only if used by the selected host
├── src/
│   ├── api.py                 # FastAPI application (verify current route)
│   ├── pipeline.py            # End-to-end orchestration
│   ├── schemas.py             # Request/response contracts
│   ├── audio/                 # Audio preprocessing, transcription, diarization
│   ├── nlp/                   # Intent/sentiment processing
│   ├── scoring/               # Deal scoring
│   └── reasoning/             # Evidence explanation
├── frontend/
│   ├── src/
│   │   ├── components/        # Uploader, VoiceRecorder, Result, etc.
│   │   ├── api.js             # Central API configuration/client
│   │   └── ...
│   └── package.json
├── tests/
├── scripts/
└── data/
    └── samples/               # Non-sensitive demo samples only
```

This is a suggested documentation-oriented structure based on paths referenced in the conversations. Confirm the actual repository before moving files or creating duplicates.

### Git and secret hygiene

- Keep `.env`, private recordings, raw datasets, and model weights out of source control unless there is a deliberate, secure reason.
- Keep `.env.example` limited to placeholder variable names.
- Use small, focused commits with descriptive messages.
- Verify `git status` before committing.
- Do not treat GitHub visibility or frontend obfuscation as a substitute for secret management.

---

## 19. Demo Narrative

A concise demo should follow this order:

1. **Introduce the problem:** sales calls contain buying signals and risks that are hard to evaluate consistently.
2. **Show input:** upload a sample audio file or record a short consented sample.
3. **Show the pipeline:** ingestion → transcription → diarization → exchange segmentation → signal analysis → scoring → reasoning.
4. **Show the transcript:** demonstrate speaker labels and timestamps.
5. **Show the evidence:** point to a buyer objection and the response that followed it.
6. **Show the result:** verdict, estimated score, positives, and risks.
7. **Explain the limitation:** the current score is heuristic and not calibrated against representative real deal outcomes.
8. **Close with the roadmap:** history, deployment, evaluation, and real-world calibration.

### Example from the local demo

The sample conversation contained a price objection, an offer of a discounted pilot, and a buyer response about checking with a CFO and returning early the next week. The system returned a **72.3% “Leaning positive”** estimate and flagged both positive signals and risks.

This example demonstrates the desired interaction pattern. It does **not** establish that a real deal had a 72.3% chance of closing.

---

## 20. Final Product Positioning

### Short description

**DealSense is an AI-powered sales-meeting intelligence tool that converts meeting audio into speaker-labelled transcripts, analyses key conversation exchanges, and explains the positive signals and risks behind an estimated deal outcome.**

### One-line pitch

**Know what your sales conversation is telling you—and why.**

### Product promise

DealSense should help people review conversations more thoughtfully, not replace their judgement with an unexplained number. The strongest version of this product will combine reliable transcription, faithful evidence extraction, calibrated outcome estimates, privacy-conscious handling, and a polished interface that makes complex analysis easy to understand.

---

## Appendix A — Source Notes

This blueprint consolidates the two user-provided conversation exports:

1. **“Meeting outcome prediction from audio transcripts”** — initial product concept, dataset discussion, architecture, model plan, backend build, and successful local demo.
2. **“Read this”** — frontend continuation, React/Vite UI, voice recording, automatic transcription after stopping, pipeline graph request, Dashboard/History/Settings request, API URL configuration, and deployment exploration.

Items explicitly described as *proposed*, *planned*, *recommended*, or *not confirmed* are product-management synthesis or open decisions—not claims that the feature is already implemented. No outside research was added to this document.
