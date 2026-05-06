const pptxgen = require('pptxgenjs');
const html2pptx = require('/home/z/my-project/skills/ppt/scripts/html2pptx');
const fs = require('fs');
const path = require('path');

const WS = '/home/z/my-project/al/docs/pptx-workspace';

// Ocean theme colors
const C = {
  'primary-100':'#0D1525','primary-90':'#122040','primary-80':'#1B2A4A',
  'primary-60':'#3D5A80','primary-40':'#6B8AB0','primary-20':'#B0C4DE',
  'primary-10':'#DFE8F2','primary-5':'#F0F4F8',
  'accent':'#2A9D8F','on-dark':'#FFFFFF','on-dark-s':'rgba(255,255,255,0.7)',
  'bg':'#FFFFFF','surface':'#F0F4F8','card':'#FFFFFF'
};

function html(bodyStyle, content) {
  return `<!DOCTYPE html><html><head><meta charset="utf-8"></head>
<body style="width:720pt;height:405pt;margin:0;padding:0;overflow:hidden;${bodyStyle}font-family:'Microsoft YaHei','SimHei',sans-serif;">${content}</body></html>`;
}

const slides = [];

// ===== SLIDE 1: COVER =====
slides.push(html(`background-image:url('${WS}/cover-bg.png');background-size:cover;display:flex;flex-direction:column;`, `
<div style="position:absolute;top:0;left:0;width:720pt;height:405pt;background-color:rgba(18,32,64,0.80);"></div>
<div style="position:relative;z-index:1;flex:1;display:flex;flex-direction:column;justify-content:center;align-items:center;padding:0 80pt;">
  <div style="width:48pt;height:3pt;background:${C.accent};margin:0 0 24pt 0;"></div>
  <h1 style="font-size:36pt;font-weight:bold;color:${C['on-dark']};text-align:center;line-height:1.2;margin:0;">ИИ-тьютор для СПО</h1>
  <p style="font-size:20pt;color:${C['on-dark-s']};text-align:center;margin:16pt 0 0 0;line-height:1.3;">Интеллектуальная система на базе LLM<br/>для среднего профессионального образования</p>
  <div style="width:48pt;height:3pt;background:${C.accent};margin:28pt 0;"></div>
  <p style="font-size:14pt;color:${C['on-dark-s']};text-align:center;margin:0;line-height:1.6;">ГБПОУ РО «Сальский индустриальный техникум»</p>
  <p style="font-size:13pt;color:${C['on-dark-s']};text-align:center;margin:8pt 0 0 0;">Бардаков Д.Н. · Мышанская Н.Г. · 2026</p>
</div>`));

// ===== SLIDE 2: TOC =====
slides.push(html(`background-color:${C.bg};display:flex;flex-direction:column;`, `
<div style="padding:36pt 48pt 20pt 48pt;">
  <h2 style="font-size:28pt;font-weight:bold;color:${C['primary-80']};margin:0;">Содержание</h2>
</div>
<div style="flex:1;padding:0 48pt;display:flex;flex-direction:column;justify-content:center;">
  <div style="display:flex;align-items:center;padding:12pt 20pt;background:${C.surface};border-radius:8pt;margin-bottom:8pt;">
    <p style="font-size:52pt;font-weight:bold;color:rgba(27,42,74,0.06);margin:0;line-height:1;position:absolute;right:56pt;">01</p>
    <div style="width:3pt;height:28pt;background:${C.accent};margin:0 16pt 0 0;border-radius:2pt;"></div>
    <p style="font-size:17pt;font-weight:bold;color:${C['primary-80']};margin:0;">Проблематика и решение</p>
  </div>
  <div style="display:flex;align-items:center;padding:12pt 20pt;background:${C.surface};border-radius:8pt;margin-bottom:8pt;">
    <p style="font-size:52pt;font-weight:bold;color:rgba(27,42,74,0.06);margin:0;line-height:1;position:absolute;right:56pt;">02</p>
    <div style="width:3pt;height:28pt;background:${C.accent};margin:0 16pt 0 0;border-radius:2pt;"></div>
    <p style="font-size:17pt;font-weight:bold;color:${C['primary-80']};margin:0;">Архитектура и функционал</p>
  </div>
  <div style="display:flex;align-items:center;padding:12pt 20pt;background:${C.surface};border-radius:8pt;margin-bottom:8pt;">
    <p style="font-size:52pt;font-weight:bold;color:rgba(27,42,74,0.06);margin:0;line-height:1;position:absolute;right:56pt;">03</p>
    <div style="width:3pt;height:28pt;background:${C.accent};margin:0 16pt 0 0;border-radius:2pt;"></div>
    <p style="font-size:17pt;font-weight:bold;color:${C['primary-80']};margin:0;">Текущий статус и дорожная карта</p>
  </div>
  <div style="display:flex;align-items:center;padding:12pt 20pt;background:${C.surface};border-radius:8pt;margin-bottom:8pt;">
    <p style="font-size:52pt;font-weight:bold;color:rgba(27,42,74,0.06);margin:0;line-height:1;position:absolute;right:56pt;">04</p>
    <div style="width:3pt;height:28pt;background:${C.accent};margin:0 16pt 0 0;border-radius:2pt;"></div>
    <p style="font-size:17pt;font-weight:bold;color:${C['primary-80']};margin:0;">Безопасность и риски</p>
  </div>
  <div style="display:flex;align-items:center;padding:12pt 20pt;background:${C.surface};border-radius:8pt;">
    <p style="font-size:52pt;font-weight:bold;color:rgba(27,42,74,0.06);margin:0;line-height:1;position:absolute;right:56pt;">05</p>
    <div style="width:3pt;height:28pt;background:${C.accent};margin:0 16pt 0 0;border-radius:2pt;"></div>
    <p style="font-size:17pt;font-weight:bold;color:${C['primary-80']};margin:0;">Команда и следующие шаги</p>
  </div>
</div>`));

// ===== SLIDE 3: PROBLEM (dark) =====
slides.push(html(`background-color:${C['primary-90']};display:flex;flex-direction:column;`, `
<div style="height:4pt;background:${C.accent};"></div>
<div style="padding:20pt 40pt 0 40pt;">
  <p style="font-size:12pt;color:${C.accent};letter-spacing:2pt;margin:0 0 4pt 0;">ПРОБЛЕМАТИКА</p>
  <span style="font-size:24pt;font-weight:bold;color:${C['on-dark']};white-space:nowrap;">Дисбаланс учебного процесса</span>
  <div style="width:40pt;height:3pt;background:${C.accent};margin:8pt 0;"></div>
</div>
<div style="padding:10pt 40pt 24pt 40pt;display:flex;flex-direction:column;gap:8pt;">
  <div style="background:rgba(255,255,255,0.08);border:1pt solid rgba(255,255,255,0.15);border-radius:8pt;padding:10pt 16pt;display:flex;align-items:center;gap:10pt;">
    <div style="width:24pt;height:24pt;background:${C.accent};border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;"><p style="font-size:12pt;font-weight:bold;color:#FFFFFF;margin:0;line-height:1;">1</p></div>
    <div><p style="font-size:14pt;font-weight:bold;color:${C['on-dark']};margin:0;">70% времени — теория</p><p style="font-size:12pt;color:${C['on-dark-s']};line-height:1.3;margin:2pt 0 0 0;">Аудиторные часы уходят на изложение лекций</p></div>
  </div>
  <div style="background:rgba(255,255,255,0.08);border:1pt solid rgba(255,255,255,0.15);border-radius:8pt;padding:10pt 16pt;display:flex;align-items:center;gap:10pt;">
    <div style="width:24pt;height:24pt;background:${C.accent};border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;"><p style="font-size:12pt;font-weight:bold;color:#FFFFFF;margin:0;line-height:1;">2</p></div>
    <div><p style="font-size:14pt;font-weight:bold;color:${C['on-dark']};margin:0;">30% времени — практика</p><p style="font-size:12pt;color:${C['on-dark-s']};line-height:1.3;margin:2pt 0 0 0;">Практика — ключевой компонент подготовки</p></div>
  </div>
  <div style="background:rgba(255,255,255,0.08);border:1pt solid rgba(255,255,255,0.15);border-radius:8pt;padding:10pt 16pt;display:flex;align-items:center;gap:10pt;">
    <div style="width:24pt;height:24pt;background:${C.accent};border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;"><p style="font-size:12pt;font-weight:bold;color:#FFFFFF;margin:0;line-height:1;">3</p></div>
    <div><p style="font-size:14pt;font-weight:bold;color:${C['on-dark']};margin:0;">Слабая обратная связь</p><p style="font-size:12pt;color:${C['on-dark-s']};line-height:1.3;margin:2pt 0 0 0;">Студенты не проверяют понимание до практики</p></div>
  </div>
  <div style="background:rgba(255,255,255,0.08);border:1pt solid rgba(255,255,255,0.15);border-radius:8pt;padding:10pt 16pt;display:flex;align-items:center;gap:10pt;">
    <div style="width:24pt;height:24pt;background:${C.accent};border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;"><p style="font-size:12pt;font-weight:bold;color:#FFFFFF;margin:0;line-height:1;">4</p></div>
    <div><p style="font-size:14pt;font-weight:bold;color:${C['on-dark']};margin:0;">Рутинная нагрузка преподавателя</p><p style="font-size:12pt;color:${C['on-dark-s']};line-height:1.3;margin:2pt 0 0 0;">Повторное объяснение материала разным группам</p></div>
  </div>
</div>`));

// ===== SLIDE 4: SOLUTION (dark split) =====
slides.push(html(`background-color:${C['primary-90']};display:flex;flex-direction:column;`, `
<div style="display:flex;height:405pt;">
  <div style="width:250pt;background:${C.accent};padding:40pt 28pt;display:flex;flex-direction:column;justify-content:center;">
    <p style="font-size:13pt;color:rgba(255,255,255,0.7);letter-spacing:2pt;margin:0 0 12pt 0;">РЕШЕНИЕ</p>
    <span style="font-size:34pt;font-weight:bold;color:#FFFFFF;line-height:1.15;">ИИ-тьютор</span>
    <div style="width:32pt;height:3pt;background:rgba(255,255,255,0.5);margin:16pt 0;"></div>
    <p style="font-size:14pt;color:rgba(255,255,255,0.85);line-height:1.5;margin:0;">Перенос теории на самостоятельную работу с ИИ-поддержкой</p>
  </div>
  <div style="flex:1;padding:32pt 36pt;display:flex;flex-direction:column;justify-content:center;gap:14pt;">
    <div style="display:flex;align-items:flex-start;gap:10pt;">
      <div style="width:4pt;height:36pt;background:${C.accent};flex-shrink:0;border-radius:2pt;margin-top:3pt;"></div>
      <div><p style="font-size:15pt;font-weight:bold;color:${C['on-dark']};margin:0 0 3pt 0;">Студент изучает теорию дома</p>
        <p style="font-size:13pt;color:${C['on-dark-s']};line-height:1.4;margin:0;">Конспекты, тесты для самопроверки, диалоговый помощник</p></div>
    </div>
    <div style="display:flex;align-items:flex-start;gap:10pt;">
      <div style="width:4pt;height:36pt;background:${C.accent};flex-shrink:0;border-radius:2pt;margin-top:3pt;"></div>
      <div><p style="font-size:15pt;font-weight:bold;color:${C['on-dark']};margin:0 0 3pt 0;">Преподаватель фокусируется на практике</p>
        <p style="font-size:13pt;color:${C['on-dark-s']};line-height:1.4;margin:0;">Отработка навыков, разбор сложных случаев, индивидуальная работа</p></div>
    </div>
    <div style="display:flex;align-items:flex-start;gap:10pt;">
      <div style="width:4pt;height:36pt;background:${C.accent};flex-shrink:0;border-radius:2pt;margin-top:3pt;"></div>
      <div><p style="font-size:15pt;font-weight:bold;color:${C['on-dark']};margin:0 0 3pt 0;">Интеграция с Moodle</p>
        <p style="font-size:13pt;color:${C['on-dark-s']};line-height:1.4;margin:0;">Кнопка «Создать конспект» прямо в интерфейсе ЭОС</p></div>
    </div>
    <div style="display:flex;align-items:flex-start;gap:10pt;">
      <div style="width:4pt;height:36pt;background:${C.accent};flex-shrink:0;border-radius:2pt;margin-top:3pt;"></div>
      <div><p style="font-size:15pt;font-weight:bold;color:${C['on-dark']};margin:0 0 3pt 0;">Ожидаемый эффект</p>
        <p style="font-size:13pt;color:${C['on-dark-s']};line-height:1.4;margin:0;">+15-20% средний балл · +40% времени на практику</p></div>
    </div>
  </div>
</div>`));

// ===== SLIDE 5: HOW IT WORKS =====
slides.push(html(`background-color:${C.bg};display:flex;flex-direction:column;`, `
<div style="width:720pt;height:56pt;background:${C['primary-90']};display:flex;align-items:center;padding:0 48pt;">
  <h2 style="font-size:22pt;font-weight:bold;color:${C['on-dark']};margin:0;">Как это работает</h2>
</div>
<div style="flex:1;padding:20pt 48pt 32pt 48pt;display:flex;flex-direction:column;justify-content:center;gap:16pt;">
  <div style="display:flex;align-items:center;gap:16pt;">
    <div style="width:44pt;height:44pt;background:${C.accent};border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;">
      <p style="font-size:18pt;font-weight:bold;color:#FFFFFF;margin:0;">1</p></div>
    <div><p style="font-size:15pt;font-weight:bold;color:${C['primary-80']};margin:0;">Преподаватель загружает лекцию в Moodle</p>
      <p style="font-size:13pt;color:${C['primary-60']};margin:2pt 0 0 0;">Текст лекции через привычный интерфейс ЭОС</p></div>
    <div style="width:28pt;height:2pt;background:${C['primary-20']};flex-shrink:0;"></div>
    <div style="width:44pt;height:44pt;background:${C.accent};border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;">
      <p style="font-size:18pt;font-weight:bold;color:#FFFFFF;margin:0;">2</p></div>
    <div><p style="font-size:15pt;font-weight:bold;color:${C['primary-80']};margin:0;">Студент нажимает «Создать конспект»</p>
      <p style="font-size:13pt;color:${C['primary-60']};margin:2pt 0 0 0;">Одна кнопка в интерфейсе Moodle</p></div>
  </div>
  <div style="display:flex;align-items:center;gap:16pt;">
    <div style="width:44pt;height:44pt;background:${C.accent};border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;">
      <p style="font-size:18pt;font-weight:bold;color:#FFFFFF;margin:0;">3</p></div>
    <div><p style="font-size:15pt;font-weight:bold;color:${C['primary-80']};margin:0;">ИИ-тьютор генерирует материалы (3-5 сек)</p>
      <p style="font-size:13pt;color:${C['primary-60']};margin:2pt 0 0 0;">Конспект, тесты, объяснения — на сервере техникума</p></div>
    <div style="width:28pt;height:2pt;background:${C['primary-20']};flex-shrink:0;"></div>
    <div style="width:44pt;height:44pt;background:${C.accent};border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;">
      <p style="font-size:18pt;font-weight:bold;color:#FFFFFF;margin:0;">4</p></div>
    <div><p style="font-size:15pt;font-weight:bold;color:${C['primary-80']};margin:0;">Студент изучает и проверяет знания</p>
      <p style="font-size:13pt;color:${C['primary-60']};margin:2pt 0 0 0;">Тесты для самопроверки, диалог с тьютором</p></div>
  </div>
  <div style="display:flex;align-items:center;justify-content:center;margin-top:8pt;">
    <div style="width:44pt;height:44pt;background:${C.accent};border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;">
      <p style="font-size:18pt;font-weight:bold;color:#FFFFFF;margin:0;">5</p></div>
    <div style="margin-left:16pt;"><p style="font-size:15pt;font-weight:bold;color:${C['primary-80']};margin:0;">Преподаватель видит статистику и корректирует процесс</p>
      <p style="font-size:13pt;color:${C['primary-60']};margin:2pt 0 0 0;">Аналитика использования, выявление сложных тем</p></div>
  </div>
</div>`));

// ===== SLIDE 6: FEATURES (2x2 grid) =====
slides.push(html(`background-color:${C.surface};display:flex;flex-direction:column;`, `
<div style="width:720pt;height:56pt;background:${C['primary-90']};display:flex;align-items:center;padding:0 48pt;">
  <h2 style="font-size:22pt;font-weight:bold;color:${C['on-dark']};margin:0;">Функционал ИИ-тьютора</h2>
</div>
<div style="flex:1;display:flex;flex-direction:column;padding:12pt 48pt 24pt 48pt;gap:10pt;">
  <div style="display:flex;gap:12pt;">
    <div style="width:296pt;flex-shrink:0;background:${C.card};border-radius:10pt;padding:14pt;border-left:4pt solid ${C.accent};box-shadow:0 2pt 6pt rgba(0,0,0,0.06);">
      <p style="font-size:15pt;font-weight:bold;color:${C['primary-80']};margin:0 0 4pt 0;">Конспекты лекций</p>
      <p style="font-size:12pt;color:${C['primary-60']};line-height:1.4;margin:0;">Автоматическая генерация конспектов. Два уровня: базовый и углублённый</p>
    </div>
    <div style="width:296pt;flex-shrink:0;background:${C.card};border-radius:10pt;padding:14pt;border-left:4pt solid ${C.accent};box-shadow:0 2pt 6pt rgba(0,0,0,0.06);">
      <p style="font-size:15pt;font-weight:bold;color:${C['primary-80']};margin:0 0 4pt 0;">Тесты для самопроверки</p>
      <p style="font-size:12pt;color:${C['primary-60']};line-height:1.4;margin:0;">Вопросы с вариантами ответов. Три уровня сложности</p>
    </div>
  </div>
  <div style="display:flex;gap:12pt;">
    <div style="width:296pt;flex-shrink:0;background:${C.card};border-radius:10pt;padding:14pt;border-left:4pt solid ${C.accent};box-shadow:0 2pt 6pt rgba(0,0,0,0.06);">
      <p style="font-size:15pt;font-weight:bold;color:${C['primary-80']};margin:0 0 4pt 0;">Объяснение терминов</p>
      <p style="font-size:12pt;color:${C['primary-60']};line-height:1.4;margin:0;">Подробное объяснение понятий простым языком с примерами</p>
    </div>
    <div style="width:296pt;flex-shrink:0;background:${C.card};border-radius:10pt;padding:14pt;border-left:4pt solid ${C.accent};box-shadow:0 2pt 6pt rgba(0,0,0,0.06);">
      <p style="font-size:15pt;font-weight:bold;color:${C['primary-80']};margin:0 0 4pt 0;">Диалоговый помощник</p>
      <p style="font-size:12pt;color:${C['primary-60']};line-height:1.4;margin:0;">Уточняющие вопросы по лекции в формате диалога</p>
    </div>
  </div>
  <div style="background:${C['primary-10']};border-radius:10pt;padding:14pt;border-left:4pt solid ${C.accent};">
    <p style="font-size:15pt;font-weight:bold;color:${C['primary-80']};margin:0 0 4pt 0;">Адаптация для студентов с ОВЗ</p>
    <p style="font-size:12pt;color:${C['primary-60']};line-height:1.4;margin:0;">Упрощённая версия материалов: короткие предложения, простой язык, инклюзивный подход</p>
  </div>
</div>`));

// ===== SLIDE 7: SECURITY (split) =====
slides.push(html(`background-color:${C.bg};display:flex;flex-direction:column;`, `
<div style="width:720pt;height:56pt;background:${C['primary-90']};display:flex;align-items:center;padding:0 48pt;">
  <h2 style="font-size:22pt;font-weight:bold;color:${C['on-dark']};margin:0;">Безопасность данных</h2>
</div>
<div style="flex:1;display:flex;padding:0 48pt;gap:20pt;align-items:center;">
  <div style="width:296pt;flex-shrink:0;">
    <div style="width:40pt;height:3pt;background:${C.accent};margin:0 0 12pt 0;"></div>
    <p style="font-size:18pt;font-weight:bold;color:${C['primary-80']};margin:0 0 8pt 0;">Приоритет — защита данных</p>
    <p style="font-size:14pt;color:${C['primary-60']};line-height:1.6;margin:0;">Персональные данные студентов не покидают территорию техникума. В отличие от ChatGPT и аналогов, данные не отправляются на сторонние серверы.</p>
  </div>
  <div style="width:1pt;height:160pt;background:${C['primary-10']};"></div>
  <div style="width:296pt;flex-shrink:0;">
    <div style="width:40pt;height:3pt;background:${C.accent};margin:0 0 12pt 0;"></div>
    <p style="font-size:18pt;font-weight:bold;color:${C['primary-80']};margin:0 0 8pt 0;">Соответствие ФЗ-152</p>
    <p style="font-size:14pt;color:${C['primary-60']};line-height:1.6;margin:0;">Система спроектирована с учётом требований законодательства. Сервер полностью изолирован от интернета.</p>
  </div>
</div>
<div style="padding:0 48pt 32pt 48pt;">
  <div style="background:${C['primary-5']};border-radius:8pt;padding:14pt 20pt;border:1pt solid ${C['primary-10']};">
    <p style="font-size:13pt;color:${C['primary-60']};margin:0;line-height:1.5;"><b style="color:${C['primary-80']};">Локальное развёртывание:</b> Модель и все данные находятся на собственном сервере техникума. Доступ в интернет для обработки не требуется.</p>
  </div>
</div>`));

// ===== SLIDE 8: STATUS (KPI) =====
slides.push(html(`background-color:${C.bg};display:flex;flex-direction:column;`, `
<div style="width:720pt;height:56pt;background:${C['primary-90']};display:flex;align-items:center;padding:0 48pt;">
  <h2 style="font-size:22pt;font-weight:bold;color:${C['on-dark']};margin:0;">Текущий статус проекта</h2>
</div>
<div style="flex:1;display:flex;flex-direction:column;justify-content:center;padding:16pt 48pt 32pt 48pt;">
  <div style="display:flex;gap:16pt;margin-bottom:20pt;">
    <div style="width:192pt;flex-shrink:0;background:${C.card};border-radius:10pt;padding:24pt 16pt;text-align:center;box-shadow:0 3pt 10pt rgba(0,0,0,0.08);">
      <p style="font-size:44pt;font-weight:bold;color:${C.accent};margin:0;">33%</p>
      <p style="font-size:13pt;color:${C['primary-40']};margin:6pt 0 0 0;line-height:1.4;">Общий прогресс выполнения</p>
    </div>
    <div style="width:192pt;flex-shrink:0;background:${C.card};border-radius:10pt;padding:24pt 16pt;text-align:center;box-shadow:0 3pt 10pt rgba(0,0,0,0.08);">
      <p style="font-size:44pt;font-weight:bold;color:${C.accent};margin:0;">67</p>
      <p style="font-size:13pt;color:${C['primary-40']};margin:6pt 0 0 0;line-height:1.4;">Лекций оцифровано</p>
    </div>
    <div style="width:192pt;flex-shrink:0;background:${C.card};border-radius:10pt;padding:24pt 16pt;text-align:center;box-shadow:0 3pt 10pt rgba(0,0,0,0.08);">
      <p style="font-size:44pt;font-weight:bold;color:${C.accent};margin:0;">771</p>
      <p style="font-size:13pt;color:${C['primary-40']};margin:6pt 0 0 0;line-height:1.4;">Записей в датасете</p>
    </div>
  </div>
  <div style="display:flex;gap:16pt;">
    <div style="width:192pt;flex-shrink:0;background:${C.card};border-radius:10pt;padding:20pt 16pt;text-align:center;box-shadow:0 3pt 10pt rgba(0,0,0,0.08);">
      <p style="font-size:36pt;font-weight:bold;color:${C['primary-80']};margin:0;">96%</p>
      <p style="font-size:13pt;color:${C['primary-40']};margin:4pt 0 0 0;">Датасет готов</p>
    </div>
    <div style="width:192pt;flex-shrink:0;background:${C.card};border-radius:10pt;padding:20pt 16pt;text-align:center;box-shadow:0 3pt 10pt rgba(0,0,0,0.08);">
      <p style="font-size:36pt;font-weight:bold;color:${C['primary-80']};margin:0;">2</p>
      <p style="font-size:13pt;color:${C['primary-40']};margin:4pt 0 0 0;">Предметных области</p>
    </div>
    <div style="width:192pt;flex-shrink:0;background:${C.card};border-radius:10pt;padding:20pt 16pt;text-align:center;box-shadow:0 3pt 10pt rgba(0,0,0,0.08);">
      <p style="font-size:36pt;font-weight:bold;color:${C['primary-80']};margin:0;">3 сек</p>
      <p style="font-size:13pt;color:${C['primary-40']};margin:4pt 0 0 0;">Генерация конспекта</p>
    </div>
  </div>
</div>`));

// ===== SLIDE 9: ROADMAP (timeline vertical) =====
slides.push(html(`background-color:${C.bg};display:flex;flex-direction:column;`, `
<div style="width:720pt;height:56pt;background:${C['primary-90']};display:flex;align-items:center;padding:0 48pt;">
  <h2 style="font-size:22pt;font-weight:bold;color:${C['on-dark']};margin:0;">Дорожная карта</h2>
</div>
<div style="flex:1;padding:16pt 48pt 28pt 48pt;display:flex;flex-direction:column;justify-content:center;gap:10pt;">
  <div style="display:flex;align-items:center;gap:14pt;">
    <div style="width:56pt;flex-shrink:0;text-align:right;"><p style="font-size:11pt;font-weight:bold;color:${C.accent};margin:0;">Q1 2026</p></div>
    <div style="width:12pt;height:12pt;background:${C.accent};border-radius:50%;flex-shrink:0;"></div>
    <div style="width:480pt;background:${C['primary-5']};border-radius:6pt;padding:10pt 16pt;border-left:3pt solid ${C.accent};">
      <p style="font-size:14pt;font-weight:bold;color:${C['primary-80']};margin:0;">Прототип</p>
      <p style="font-size:12pt;color:${C['primary-60']};margin:2pt 0 0 0;">Базовая модель, генерация конспектов, класс IntelligentTutor</p></div>
  </div>
  <div style="display:flex;align-items:center;gap:14pt;">
    <div style="width:56pt;flex-shrink:0;text-align:right;"><p style="font-size:11pt;font-weight:bold;color:${C.accent};margin:0;">Q2 2026</p></div>
    <div style="width:12pt;height:12pt;background:${C.accent};border-radius:50%;flex-shrink:0;"></div>
    <div style="width:480pt;background:${C['primary-5']};border-radius:6pt;padding:10pt 16pt;border-left:3pt solid ${C['primary-20']};">
      <p style="font-size:14pt;font-weight:bold;color:${C['primary-80']};margin:0;">Инфраструктура</p>
      <p style="font-size:12pt;color:${C['primary-60']};margin:2pt 0 0 0;">Закупка GPU, установка, настройка</p></div>
  </div>
  <div style="display:flex;align-items:center;gap:14pt;">
    <div style="width:56pt;flex-shrink:0;text-align:right;"><p style="font-size:11pt;font-weight:bold;color:${C.accent};margin:0;">Q3 2026</p></div>
    <div style="width:12pt;height:12pt;background:${C['primary-20']};border-radius:50%;flex-shrink:0;"></div>
    <div style="width:480pt;background:${C['primary-5']};border-radius:6pt;padding:10pt 16pt;border-left:3pt solid ${C['primary-20']};">
      <p style="font-size:14pt;font-weight:bold;color:${C['primary-80']};margin:0;">Дообучение модели</p>
      <p style="font-size:12pt;color:${C['primary-60']};margin:2pt 0 0 0;">Fine-tuning на датасете СИТ, LoRA-адаптеры, валидация</p></div>
  </div>
  <div style="display:flex;align-items:center;gap:14pt;">
    <div style="width:56pt;flex-shrink:0;text-align:right;"><p style="font-size:11pt;font-weight:bold;color:${C.accent};margin:0;">Q4 2026</p></div>
    <div style="width:12pt;height:12pt;background:${C['primary-20']};border-radius:50%;flex-shrink:0;"></div>
    <div style="width:480pt;background:${C['primary-5']};border-radius:6pt;padding:10pt 16pt;border-left:3pt solid ${C['primary-20']};">
      <p style="font-size:14pt;font-weight:bold;color:${C['primary-80']};margin:0;">Пилотное внедрение</p>
      <p style="font-size:12pt;color:${C['primary-60']};margin:2pt 0 0 0;">Запуск в группе 15.02.14, сбор обратной связи</p></div>
  </div>
  <div style="display:flex;align-items:center;gap:14pt;">
    <div style="width:56pt;flex-shrink:0;text-align:right;"><p style="font-size:11pt;font-weight:bold;color:${C.accent};margin:0;">Q1 2027</p></div>
    <div style="width:12pt;height:12pt;background:${C['primary-20']};border-radius:50%;flex-shrink:0;"></div>
    <div style="width:480pt;background:${C['primary-5']};border-radius:6pt;padding:10pt 16pt;border-left:3pt solid ${C['primary-20']};">
      <p style="font-size:14pt;font-weight:bold;color:${C['primary-80']};margin:0;">Продакшен-релиз</p>
      <p style="font-size:12pt;color:${C['primary-60']};margin:2pt 0 0 0;">Расширение на все специальности, Apache 2.0</p></div>
  </div>
</div>`));

// ===== SLIDE 10: RISKS =====
slides.push(html(`background-color:${C.surface};display:flex;flex-direction:column;`, `
<div style="width:720pt;height:56pt;background:${C['primary-90']};display:flex;align-items:center;padding:0 48pt;">
  <h2 style="font-size:22pt;font-weight:bold;color:${C['on-dark']};margin:0;">Риски и митигация</h2>
</div>
<div style="flex:1;display:flex;padding:0 48pt 32pt 48pt;gap:20pt;align-items:center;">
  <div style="width:296pt;flex-shrink:0;background:${C.card};border:1.5pt solid #E8B4B8;border-radius:10pt;padding:20pt;">
    <p style="font-size:16pt;font-weight:bold;color:#C0392B;margin:0 0 12pt 0;">Риски</p>
    <ul style="font-size:14pt;color:${C['primary-60']};margin:0;padding-left:18pt;line-height:1.8;">
      <li>Ошибки генерации модели (галлюцинации)</li>
      <li>Задержка закупки сервера</li>
      <li>Недостаточный объём датасета</li>
      <li>Низкий уровень ИТ-грамотности</li>
      <li>Сопротивление преподавателей</li>
    </ul>
  </div>
  <div style="width:296pt;flex-shrink:0;background:${C.card};border:1.5pt solid #B8D8C8;border-radius:10pt;padding:20pt;">
    <p style="font-size:16pt;font-weight:bold;color:#27AE60;margin:0 0 12pt 0;">Митигация</p>
    <ul style="font-size:14pt;color:${C['primary-60']};margin:0;padding-left:18pt;line-height:1.8;">
      <li>Проверка ответов преподавателем</li>
      <li>План B: облачный GPU на период закупки</li>
      <li>Датасет уже 771 запись, готов к обучению</li>
      <li>Интеграция в Moodle (привычный интерфейс)</li>
      <li>Презентации и FAQ для коллектива</li>
    </ul>
  </div>
</div>`));

// ===== SLIDE 11: TEAM =====
slides.push(html(`background-color:${C.bg};display:flex;flex-direction:column;`, `
<div style="width:720pt;height:56pt;background:${C['primary-90']};display:flex;align-items:center;padding:0 48pt;">
  <h2 style="font-size:22pt;font-weight:bold;color:${C['on-dark']};margin:0;">Проектная команда</h2>
</div>
<div style="flex:1;display:flex;flex-direction:column;justify-content:center;padding:20pt 48pt 32pt 48pt;gap:20pt;">
  <div style="display:flex;gap:16pt;">
    <div style="width:296pt;background:${C.card};border-radius:10pt;padding:24pt;box-shadow:0 3pt 10pt rgba(0,0,0,0.08);">
      <div style="width:48pt;height:48pt;background:${C.accent};border-radius:50%;margin:0 0 14pt 0;"></div>
      <p style="font-size:18pt;font-weight:bold;color:${C['primary-80']};margin:0 0 4pt 0;">Бардаков Д.Н.</p>
      <p style="font-size:14pt;color:${C.accent};margin:0 0 10pt 0;font-weight:bold;">Руководитель проекта</p>
      <p style="font-size:13pt;color:${C['primary-60']};line-height:1.5;margin:0;">Архитектура системы, разработка программного обеспечения, ML-инженерия, серверная инфраструктура</p>
    </div>
    <div style="width:296pt;background:${C.card};border-radius:10pt;padding:24pt;box-shadow:0 3pt 10pt rgba(0,0,0,0.08);">
      <div style="width:48pt;height:48pt;background:${C.accent};border-radius:50%;margin:0 0 14pt 0;"></div>
      <p style="font-size:18pt;font-weight:bold;color:${C['primary-80']};margin:0 0 4pt 0;">Мышанская Н.Г.</p>
      <p style="font-size:14pt;color:${C.accent};margin:0 0 10pt 0;font-weight:bold;">Методист</p>
      <p style="font-size:13pt;color:${C['primary-60']};line-height:1.5;margin:0;">Разработка учебного контента, формирование датасета, методические рекомендации, валидация качества</p>
    </div>
  </div>
  <div style="background:${C['primary-5']};border-radius:8pt;padding:16pt 20pt;border:1pt solid ${C['primary-10']};">
    <p style="font-size:14pt;color:${C['primary-80']};margin:0;"><b>Организация:</b> ГБПОУ РО «Сальский индустриальный техникум» (СИТ)</p>
    <p style="font-size:14pt;color:${C['primary-80']};margin:6pt 0 0 0;"><b>Специальность:</b> 15.02.14 «Оснащение средствами автоматизации ТПиП»</p>
  </div>
</div>`));

// ===== SLIDE 12: CLOSING =====
slides.push(html(`background-color:${C['primary-100']};display:flex;flex-direction:column;`, `
<div style="height:4pt;background:${C.accent};"></div>
<div style="flex:1;display:flex;flex-direction:column;justify-content:center;align-items:center;padding:0 80pt;">
  <div style="width:10pt;height:10pt;border-radius:50%;background:${C.accent};margin-bottom:24pt;"></div>
  <h1 style="font-size:36pt;font-weight:bold;color:${C['on-dark']};text-align:center;line-height:1.2;margin:0;">Спасибо за внимание!</h1>
  <div style="width:48pt;height:3pt;background:${C.accent};margin:20pt 0;"></div>
  <p style="font-size:16pt;color:${C['on-dark-s']};text-align:center;line-height:1.5;margin:0;">Готовы ответить на ваши вопросы</p>
  <p style="font-size:14pt;color:${C['on-dark-s']};text-align:center;margin:24pt 0 0 0;line-height:1.6;">Бардаков Д.Н. · Мышанская Н.Г.</p>
  <p style="font-size:13pt;color:${C['on-dark-s']};text-align:center;margin:8pt 0 0 0;">ГБПОУ РО «Сальский индустриальный техникум» · 2026</p>
</div>`));

// ===== BUILD PPTX =====
async function build() {
  const pptx = new pptxgen();
  pptx.layout = 'LAYOUT_16x9';
  pptx.author = 'Бардаков Д.Н., Мышанская Н.Г.';
  pptx.company = 'ГБПОУ РО «Сальский индустриальный техникум»';
  pptx.title = 'ИИ-тьютор для СПО';
  pptx.subject = 'Защита проекта: Интеллектуальный тьютор на базе LLM';

  const allWarnings = [];
  for (let i = 0; i < slides.length; i++) {
    const htmlFile = path.join(WS, `slide${i+1}.html`);
    fs.writeFileSync(htmlFile, slides[i]);
    console.log(`Processing slide ${i+1}/${slides.length}...`);
    const { warnings } = await html2pptx(htmlFile, pptx, { fontConfig: { cjk: 'Microsoft YaHei', latin: 'Corbel' } });
    allWarnings.push(...warnings);
  }

  const outPath = '/home/z/my-project/al/docs/ai_tutor_presentation.pptx';
  await pptx.writeFile({ fileName: outPath });
  console.log(`\nDone! Saved to: ${outPath}`);
  if (allWarnings.length > 0) console.log('Warnings:', allWarnings);
}

build().catch(e => { console.error(e); process.exit(1); });
