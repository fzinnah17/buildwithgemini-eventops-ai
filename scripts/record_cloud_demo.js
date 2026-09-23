const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const { execSync } = require('child_process');

(async () => {
  const tempDir = path.join(process.cwd(), '.video_tmp');
  if (fs.existsSync(tempDir)) fs.rmSync(tempDir, { recursive: true, force: true });
  fs.mkdirSync(tempDir, { recursive: true });

  const demoDir = path.join(process.cwd(), 'docs/demo');
  fs.mkdirSync(demoDir, { recursive: true });

  console.log('Launching browser to record Cloud Demo (45-75s)...');
  const browser = await chromium.launch({
    executablePath: '/usr/bin/google-chrome',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const context = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    recordVideo: { dir: tempDir, size: { width: 1280, height: 800 } }
  });

  const page = await context.newPage();
  const targetUrl = 'https://eventops-ai-frontend-282776913855.us-central1.run.app';
  console.log(`Navigating to ${targetUrl}...`);
  await page.goto(targetUrl, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  // 1. Overview
  console.log('1. Displaying Overview...');
  await page.waitForTimeout(4000);

  // 2. Switch between two events to prove dynamic rendering
  console.log('2. Switching active event...');
  const selector = page.locator('#eventSelector');
  await selector.selectOption('evt_design_summit_2026');
  await page.waitForTimeout(4000);
  await selector.selectOption('evt_wit_manhattan_2026');
  await page.waitForTimeout(3000);

  // 3. Ask "What am I forgetting?"
  console.log('3. Asking "What am I forgetting?" in Copilot...');
  const chatInput = page.locator('#chatInput');
  await chatInput.click();
  await chatInput.pressSequentially('What am I forgetting for this event?', { delay: 30 });
  await page.waitForTimeout(400);
  await chatInput.press('Enter');

  // 4. Show structured EventOps Guard result
  console.log('4. Waiting for EventOps Guard result...');
  await page.waitForTimeout(10000);

  // 5. Request budget constraint change
  console.log('5. Requesting budget rebalance...');
  await chatInput.click();
  await chatInput.pressSequentially('Adjust catering to $1,800 and venue to $1,200', { delay: 25 });
  await page.waitForTimeout(400);
  await chatInput.press('Enter');

  // 6. Show proposal / Decision Ledger
  console.log('6. Waiting for budget proposal...');
  await page.waitForTimeout(10000);

  // 7. Show Risks & Decisions tab with human approval requirement
  console.log('7. Switching to Risks & Decisions tab...');
  await page.click('button[data-tab="risks"]');
  await page.waitForTimeout(5000);

  // 8. Briefly show Experience & Journey tab
  console.log('8. Showing Experience & Journey tab...');
  await page.click('button[data-tab="experience"]');
  await page.waitForTimeout(5000);

  // Return to Overview
  await page.click('button[data-tab="overview"]');
  await page.waitForTimeout(3000);

  console.log('Closing browser to finalize video recording...');
  await page.close();
  await context.close();
  await browser.close();

  const files = fs.readdirSync(tempDir).filter(f => f.endsWith('.webm'));
  if (files.length === 0) {
    console.error('No video recording found in temp dir!');
    process.exit(1);
  }

  const rawWebm = path.join(tempDir, files[0]);
  const outMp4 = path.join(demoDir, 'eventops-ai-cloud-demo.mp4');
  const outGif = path.join(demoDir, 'eventops-ai-demo.gif');

  console.log(`Converting to MP4: ${outMp4}...`);
  execSync(`ffmpeg -y -i "${rawWebm}" -c:v libx264 -preset fast -crf 22 -pix_fmt yuv420p "${outMp4}"`, { stdio: 'inherit' });
  console.log(`Saved MP4 to ${outMp4}`);

  console.log(`Generating optimized demo GIF: ${outGif}...`);
  execSync(`ffmpeg -y -i "${rawWebm}" -vf "fps=10,scale=800:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" "${outGif}"`, { stdio: 'inherit' });
  console.log(`Saved GIF to ${outGif}`);

  // Clean temp
  fs.rmSync(tempDir, { recursive: true, force: true });
  console.log('Demo recording workflow completed successfully!');
})();
