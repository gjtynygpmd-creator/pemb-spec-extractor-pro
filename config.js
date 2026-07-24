<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>PEMB Spec Extractor Pro</title>
  <link rel="stylesheet" href="styles.css">
</head>
<body>
<header>
  <div>
    <div class="eyebrow">PEMB ESTIMATOR • PROJECT INTELLIGENCE</div>
    <h1>PEMB Spec Extractor Pro</h1>
    <p>Large-file upload, processing queue, OCR, drawing review, and structured PEMB extraction.</p>
  </div>
  <div class="version">Architecture Build v0.4</div>
</header>

<main>
  <section class="panel">
    <div class="toolbar">
      <div>
        <h2>1. Create Project</h2>
        <p class="muted">Upload complete specification books, drawing sets, ZIP packages, and image scans.</p>
      </div>
      <div class="api-status" id="apiStatus">Checking processing service…</div>
    </div>
    <div class="project-grid">
      <label>Project Name<input id="projectName" placeholder="e.g., Marshall University Hangar"></label>
      <label>Customer<input id="customerName" placeholder="Owner, GC, or client"></label>
      <label>Bid Due<input id="bidDue" type="datetime-local"></label>
      <label>Project Address<input id="projectAddress" placeholder="Street, city, state, ZIP"></label>
    </div>
  </section>

  <section class="panel">
    <div class="toolbar">
      <div>
        <h2>2. Upload Bid Documents</h2>
        <p class="muted">Files upload directly to object storage in independent parts, avoiding normal browser and Netlify request limits.</p>
      </div>
      <button id="clearFiles" class="secondary">Clear</button>
    </div>

    <label class="dropzone" id="dropzone">
      <input id="fileInput" type="file" multiple
        accept=".pdf,.zip,.tif,.tiff,.png,.jpg,.jpeg,.docx,.xlsx,.dwg,.dxf">
      <strong>Drop large files or folders here</strong>
      <span>PDF, ZIP, TIFF, images, DOCX, XLSX, DWG, and DXF accepted for upload.</span>
      <span class="limit-note">Recommended part size: 16 MB. Individual files may be multiple gigabytes when cloud storage is configured.</span>
    </label>

    <div class="upload-toolbar">
      <div>
        <label class="inline">Upload mode
          <select id="uploadMode">
            <option value="cloud">Cloud multipart upload</option>
            <option value="demo">Local demonstration</option>
          </select>
        </label>
      </div>
      <button id="startUpload">Upload & Start Analysis</button>
    </div>

    <div id="fileList" class="file-list"></div>
    <div id="overallStatus" class="analysis-status"></div>
  </section>

  <section class="metrics">
    <div class="metric"><span id="fileCount">0</span><small>Files Selected</small></div>
    <div class="metric"><span id="totalSize">0 MB</span><small>Total Upload Size</small></div>
    <div class="metric"><span id="uploadedSize">0 MB</span><small>Uploaded</small></div>
    <div class="metric"><span id="jobState">Idle</span><small>Processing State</small></div>
  </section>

  <section class="panel">
    <h2>3. Processing Pipeline</h2>
    <div class="pipeline">
      <div class="stage" data-stage="upload"><b>1</b><span>Multipart Upload</span><small>Direct to storage</small></div>
      <div class="stage" data-stage="classify"><b>2</b><span>Page Classification</span><small>Specs, notes, plans, schedules</small></div>
      <div class="stage" data-stage="ocr"><b>3</b><span>OCR & Vision</span><small>Image-only sheets and drawings</small></div>
      <div class="stage" data-stage="extract"><b>4</b><span>PEMB Extraction</span><small>Fields, sources, confidence</small></div>
      <div class="stage" data-stage="review"><b>5</b><span>Estimator Review</span><small>Conflicts and corrections</small></div>
      <div class="stage" data-stage="export"><b>6</b><span>Export</span><small>Excel, Zoho, summary</small></div>
    </div>
  </section>

  <section class="panel">
    <div class="toolbar">
      <div>
        <h2>4. Recent Processing Jobs</h2>
        <p class="muted">The backend retains job status and extracted project data independently from the browser.</p>
      </div>
      <button id="refreshJobs" class="secondary">Refresh Jobs</button>
    </div>
    <div id="jobs" class="jobs empty">No processing jobs loaded.</div>
  </section>
</main>

<footer>PEMB Spec Extractor Pro • Frontend on Netlify • Direct multipart storage uploads • Server-side processing</footer>
<script src="app.js"></script>
</body>
</html>
