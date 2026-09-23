const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

(async () => {
  const imagesDir = path.join(process.cwd(), 'docs/images');
  fs.mkdirSync(imagesDir, { recursive: true });

  console.log('Launching headless browser to capture screenshots...');
  const browser = await chromium.launch({
    executablePath: '/usr/bin/google-chrome',
    args: ['--no-sandbox', '--disable-setuid-sandbox']
  });

  const page = await browser.newPage({
    viewport: { width: 1440, height: 900 }
  });

  const targetUrl = 'https://eventops-ai-frontend-282776913855.us-central1.run.app';
  console.log(`Navigating to ${targetUrl}...`);
  await page.goto(targetUrl, { waitUntil: 'networkidle' });
  await page.waitForTimeout(3000);

  // 1. Overview Tab
  console.log('Capturing 01_overview.png...');
  await page.click('button[data-tab="overview"]');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(imagesDir, '01_overview.png') });

  // 2. Multi-event selector
  console.log('Capturing 02_multievent_selector.png...');
  await page.focus('#eventSelector');
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(imagesDir, '02_multievent_selector.png') });

  // 3. Plan & Timeline Tab
  console.log('Capturing 03_plan_timeline.png...');
  await page.click('button[data-tab="plan"]');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(imagesDir, '03_plan_timeline.png') });

  // 4. EventOps Guard & Risks Tab
  console.log('Capturing 04_eventops_guard.png...');
  await page.click('button[data-tab="risks"]');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(imagesDir, '04_eventops_guard.png') });

  // 5. Decision Ledger
  console.log('Capturing 05_decision_ledger.png...');
  const ledger = page.locator('#decisionLedgerList');
  if (await ledger.count() > 0) {
    await ledger.scrollIntoViewIfNeeded();
  }
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(imagesDir, '05_decision_ledger.png') });

  // 6. Experience & Journey Tab
  console.log('Capturing 07_guest_journey.png & 08_visual_direction.png...');
  await page.click('button[data-tab="experience"]');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(imagesDir, '07_guest_journey.png') });
  const visualPanel = page.locator('.visual-grid');
  if (await visualPanel.count() > 0) {
    await visualPanel.scrollIntoViewIfNeeded();
  }
  await page.screenshot({ path: path.join(imagesDir, '08_visual_direction.png') });

  // 7. Structured Copilot interaction
  console.log('Sending message to Copilot: "What am I forgetting?"...');
  await page.click('button[data-tab="overview"]');
  const chatInput = page.locator('#chatInput');
  await chatInput.fill('What am I forgetting?');
  await page.waitForTimeout(400);
  await chatInput.press('Enter');
  console.log('Waiting 10s for Copilot response...');
  await page.waitForTimeout(10000);
  console.log('Capturing 06_copilot_structured_response.png...');
  await page.screenshot({ path: path.join(imagesDir, '06_copilot_structured_response.png') });

  // 8. Architecture / About Panel
  console.log('Capturing 09_architecture_panel.png...');
  await page.click('#btnOpenAbout');
  await page.waitForTimeout(1000);
  await page.screenshot({ path: path.join(imagesDir, '09_architecture_panel.png') });

  console.log('All 9 screenshots captured successfully in docs/images/!');
  await browser.close();
})();
