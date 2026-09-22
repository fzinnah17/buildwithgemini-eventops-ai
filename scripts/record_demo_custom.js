const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

(async () => {
  const tempDir = path.join(process.cwd(), '.video_tmp');
  if (fs.existsSync(tempDir)) fs.rmSync(tempDir, { recursive: true, force: true });
  fs.mkdirSync(tempDir, { recursive: true });

  console.log('Launching Chrome browser for demo recording...');
  const browser = await chromium.launch({
    executablePath: '/usr/bin/google-chrome',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    recordVideo: { dir: tempDir, size: { width: 1280, height: 800 } }
  });

  const page = await context.newPage();
  console.log('Navigating to http://localhost:8080...');
  await page.goto('http://localhost:8080', { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  const input = page.locator('#chatInput');

  // Turn 1: Propose budget adjustment
  const query1 = 'Propose reducing the total budget from $4,000 to $3,000 for evt_wit_manhattan_2026.';
  console.log(`[Turn 1] Typing: "${query1}"`);
  await input.click();
  await page.waitForTimeout(400);
  await input.pressSequentially(query1, { delay: 35 });
  await page.waitForTimeout(600);
  await input.press('Enter');

  console.log('Waiting for Turn 1 response & Firestore refresh...');
  await page.waitForTimeout(14000);

  // Turn 2: EventOps Guard readiness scan
  const query2 = 'Run an EventOps Guard readiness scan on evt_wit_manhattan_2026.';
  console.log(`[Turn 2] Typing: "${query2}"`);
  await input.click();
  await page.waitForTimeout(400);
  await input.pressSequentially(query2, { delay: 35 });
  await page.waitForTimeout(600);
  await input.press('Enter');

  console.log('Waiting for Turn 2 response...');
  await page.waitForTimeout(14000);

  // Hold on final view
  await page.waitForTimeout(3000);

  console.log('Closing recording session...');
  await page.close();
  await context.close();
  await browser.close();

  const files = fs.readdirSync(tempDir).filter(f => f.endsWith('.webm'));
  if (files.length === 0) {
    console.error('No webm recorded!');
    process.exit(1);
  }
  const webmPath = path.join(tempDir, files[0]);
  const outWebm = path.join(process.cwd(), 'docs/demo/eventops_demo.webm');
  fs.copyFileSync(webmPath, outWebm);
  console.log(`Raw video saved to ${outWebm}`);

  // Convert to high-quality GIF
  const outGif = path.join(process.cwd(), 'docs/demo/eventops-ai-demo.gif');
  console.log(`Converting to optimized GIF at ${outGif}...`);
  try {
    execSync(`ffmpeg -y -i "${outWebm}" -vf "fps=10,scale=800:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" "${outGif}"`, { stdio: 'inherit' });
    console.log(`Successfully generated demo GIF at ${outGif}`);
  } catch (err) {
    console.error('FFmpeg GIF generation failed:', err.message);
  }

  // Cleanup temp dir
  fs.rmSync(tempDir, { recursive: true, force: true });
})();
