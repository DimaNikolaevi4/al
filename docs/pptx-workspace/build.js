const pptxgen = require('pptxgenjs');
const html2pptx = require('/home/z/my-project/skills/ppt/scripts/html2pptx');
const path = require('path');

async function build() {
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_16x9';

  const fontConfig = {
    cjk: 'Microsoft YaHei',
    latin: 'Trebuchet MS'
  };

  const slidesDir = '/home/z/my-project/al/docs/pptx-workspace';
  const slideFiles = [
    'slide01.html',
    'slide02.html',
    'slide03.html',
    'slide04.html',
    'slide05.html',
    'slide06.html',
    'slide07.html',
    'slide08.html',
    'slide09.html',
    'slide10.html',
    'slide11.html',
    'slide12.html'
  ];

  let allWarnings = [];

  for (let i = 0; i < slideFiles.length; i++) {
    const filePath = path.join(slidesDir, slideFiles[i]);
    console.log(`Processing slide ${i + 1}: ${slideFiles[i]}`);

    try {
      const { slide, placeholders, warnings } = await html2pptx(filePath, pptx, { fontConfig });

      if (warnings && warnings.length > 0) {
        console.warn(`  Warnings for ${slideFiles[i]}:`);
        warnings.forEach(w => console.warn(`    - ${w}`));
        allWarnings.push({ slide: slideFiles[i], warnings });
      } else {
        console.log(`  OK`);
      }
    } catch (err) {
      console.error(`  ERROR on ${slideFiles[i]}: ${err.message}`);
      throw err;
    }
  }

  const outputPath = '/home/z/my-project/al/docs/ai_tutor_presentation_v2.pptx';
  await pptx.writeFile({ fileName: outputPath });
  console.log(`\nPresentation saved to: ${outputPath}`);
  console.log(`Total slides: ${slideFiles.length}`);

  if (allWarnings.length > 0) {
    console.log(`\nSummary of warnings:`);
    allWarnings.forEach(w => {
      console.log(`  ${w.slide}:`);
      w.warnings.forEach(ww => console.log(`    - ${ww}`));
    });
  }
}

build().catch(err => {
  console.error('Build failed:', err.message);
  process.exit(1);
});
