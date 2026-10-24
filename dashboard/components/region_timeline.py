"""Centered timeline with separate scales for history and forecast."""

import streamlit as st
import streamlit.components.v2 as components

from i18n import t


TIMELINE_HTML = """
<div class="timeline">
  <div class="zones">
    <span class="past"></span>
    <button class="today" type="button"></button>
    <span class="future"></span>
  </div>
  <div class="axis">
        <svg class="curve" viewBox="0 0 1000 74" preserveAspectRatio="none" role="img">
            <title></title>
            <path class="history-area"></path>
            <path class="forecast-area"></path>
            <line class="today-level" x1="0" x2="1000"></line>
            <path class="history-line"></path>
            <path class="forecast-line"></path>
            <line class="curve-cursor" y1="0" y2="74"></line>
            <circle class="curve-dot" r="4" vector-effect="non-scaling-stroke"></circle>
        </svg>
    <div class="track"></div>
    <div class="present" aria-hidden="true"></div>
    <input class="slider" type="range" min="-24" max="24" step="1">
  </div>
  <div class="ticks" aria-hidden="true">
    <span class="start"></span><span class="zero">0</span><span class="end"></span>
  </div>
  <output class="selection" aria-live="polite"></output>
    <div class="intensity"></div>
</div>
"""

TIMELINE_CSS = """
* { box-sizing: border-box; }
.timeline { font-family: Inter, "Segoe UI", sans-serif; color: #1E293B; padding: 0 2px; }
.zones { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 8px; font-size: 13px; font-weight: 600; }
.past { color: #003781; }
.future { color: #8A5300; text-align: right; }
.today { color: #003781; background: #E8F1FB; border: 1px solid #7FA6D6; border-radius: 6px; padding: 5px 12px; min-height: 32px; font: inherit; cursor: pointer; }
.today:hover { background: #D5E5F8; }
.today:focus-visible, .slider:focus-visible { outline: 2px solid #0057B8; outline-offset: 3px; }
.axis { position: relative; height: 92px; margin: 0; }
.curve { position: absolute; left: 11px; top: 0; width: calc(100% - 22px); height: 74px; overflow: visible; pointer-events: none; }
.curve path, .curve line { vector-effect: non-scaling-stroke; }
.history-area { fill: #7FA6D6; fill-opacity: .18; }
.forecast-area { fill: #E9B760; fill-opacity: .20; }
.history-line { fill: none; stroke: #003781; stroke-width: 1.5; }
.forecast-line { fill: none; stroke: #8A5300; stroke-width: 1.5; stroke-dasharray: 4 3; }
.today-level { stroke: #8293AB; stroke-width: 1; stroke-dasharray: 2 4; opacity: .65; }
.curve-cursor { stroke: var(--thumb-color, #003781); stroke-width: 1; opacity: .4; }
.curve-dot { fill: var(--thumb-color, #003781); stroke: white; stroke-width: 1.5; }
.track { position: absolute; left: 11px; right: 11px; top: 70px; height: 8px; border-radius: 4px; background: linear-gradient(to right, #7FA6D6 0%, #7FA6D6 50%, #E9B760 50%, #E9B760 100%); }
.present { position: absolute; left: 50%; top: 4px; bottom: 0; width: 2px; transform: translateX(-1px); background: #003781; pointer-events: none; }
.slider { appearance: none; -webkit-appearance: none; position: absolute; left: 0; bottom: 0; width: 100%; height: 36px; margin: 0; background: transparent; cursor: pointer; touch-action: pan-y; }
.slider::-webkit-slider-runnable-track { height: 8px; background: transparent; }
.slider::-moz-range-track { height: 8px; background: transparent; }
.slider::-webkit-slider-thumb { appearance: none; -webkit-appearance: none; width: 22px; height: 22px; margin-top: -7px; border-radius: 50%; background: var(--thumb-color, #003781); border: 3px solid white; box-shadow: 0 0 0 1px var(--thumb-color, #003781); }
.slider::-moz-range-thumb { width: 16px; height: 16px; border-radius: 50%; background: var(--thumb-color, #003781); border: 3px solid white; box-shadow: 0 0 0 1px var(--thumb-color, #003781); }
.ticks { display: grid; grid-template-columns: 1fr auto 1fr; gap: 8px; font-size: 11px; color: #5B6B82; }
.end { text-align: right; }
.zero { color: #003781; font-weight: 700; }
.selection { display: block; margin-top: 10px; text-align: center; font-size: 13px; font-weight: 600; line-height: 20px; color: var(--thumb-color, #003781); }
.intensity { text-align: center; font-size: 11px; line-height: 18px; color: #5B6B82; }
"""

TIMELINE_JS = """
export default function(component) {
    const {parentElement, data, setStateValue} = component;
    const root = parentElement.querySelector('.timeline');
    const slider = root.querySelector('.slider');
    const today = root.querySelector('.today');
    let month = data.month;
    root.querySelector('.past').textContent = data.past;
    root.querySelector('.future').textContent = data.future;
    root.querySelector('.start').textContent = data.start;
    root.querySelector('.end').textContent = data.end;
    today.textContent = data.today;
    today.title = data.reset;
    today.setAttribute('aria-label', data.reset);
    slider.setAttribute('aria-label', data.label);
    slider.setAttribute('aria-valuemin', '-24');
    slider.setAttribute('aria-valuemax', '12');
    const months = Array.from({length: 37}, (_, index) => index - 24);
    const maximum = Math.max(0, ...months.map(step => data.values[String(step)]));
    const coordinates = (step) => [
        step <= 0 ? (step + 24) / 24 * 500 : 500 + step / 12 * 500,
        maximum > 0 ? 68 - data.values[String(step)] / maximum * 60 : 68,
    ];
    const draw = (steps, prefix) => {
        const points = steps.map(coordinates);
        const line = points.map(([position, level], index) => `${index ? 'L' : 'M'}${position},${level}`).join(' ');
        root.querySelector(`.${prefix}-line`).setAttribute('d', line);
        root.querySelector(`.${prefix}-area`).setAttribute('d', `${line} L${points.at(-1)[0]},74 L${points[0][0]},74 Z`);
    };
    draw(months.filter(step => step <= 0), 'history');
    draw(months.filter(step => step >= 0), 'forecast');
    root.querySelector('.curve title').textContent = data.curve_label;
    root.querySelector('.curve').setAttribute('aria-label', data.curve_label);
    root.querySelector('.today-level').setAttribute('y1', coordinates(0)[1]);
    root.querySelector('.today-level').setAttribute('y2', coordinates(0)[1]);
    const update = (value) => {
        month = Math.max(-24, Math.min(12, value));
        slider.value = month <= 0 ? month : month * 2;
        slider.setAttribute('aria-valuenow', String(month));
        slider.setAttribute('aria-valuetext', `${data.labels[String(month)]}. ${data.value_labels[String(month)]}`);
        root.style.setProperty('--thumb-color', month > 0 ? '#8A5300' : '#003781');
        root.querySelector('.selection').textContent = data.labels[String(month)];
        root.querySelector('.intensity').textContent = data.value_labels[String(month)];
        const [position, level] = coordinates(month);
        root.querySelector('.curve-dot').setAttribute('cx', position);
        root.querySelector('.curve-dot').setAttribute('cy', level);
        root.querySelector('.curve-cursor').setAttribute('x1', position);
        root.querySelector('.curve-cursor').setAttribute('x2', position);
    };
    slider.oninput = () => {
        const position = Number(slider.value);
        update(position <= 0 ? Math.round(position) : Math.round(position / 2));
    };
    slider.onchange = () => setStateValue('month', month);
    slider.onkeydown = (event) => {
        const changes = {ArrowLeft: -1, ArrowDown: -1, ArrowRight: 1, ArrowUp: 1, PageDown: -3, PageUp: 3};
        if (!(event.key in changes) && event.key !== 'Home' && event.key !== 'End') return;
        event.preventDefault();
        update(event.key === 'Home' ? -24 : event.key === 'End' ? 12 : month + changes[event.key]);
        setStateValue('month', month);
    };
    today.onclick = () => { update(0); setStateValue('month', 0); };
    update(month);
    return () => { slider.oninput = null; slider.onchange = null; slider.onkeydown = null; today.onclick = null; };
}
"""

_timeline = components.component(
    "region_time_axis", html=TIMELINE_HTML, css=TIMELINE_CSS, js=TIMELINE_JS,
)


def _store_month() -> None:
    st.session_state.region_step = int(st.session_state.region_timeline_control["month"])


def render_timeline(labels: dict[str, str], values: dict[str, float]) -> int:
    month = int(st.session_state.get("region_step", 0))
    baseline = values["0"]
    value_labels = {}
    for step, value in values.items():
        label = t("region_intensity_value", value=f"{value:.1f}")
        if baseline > 0:
            label += " · " + t("region_intensity_change", change=f"{(value / baseline - 1) * 100:+.0f}")
        value_labels[step] = label
    _timeline(
        key="region_timeline_control",
        data={
            "month": month, "labels": labels, "label": t("region_step"),
            "values": values, "value_labels": value_labels, "curve_label": t("region_intensity_curve"),
            "past": t("region_past"), "today": t("region_now"),
            "future": t("region_forecast"), "reset": t("region_reset_today"),
            "start": t("region_month_offset", n="-24"),
            "end": t("region_month_offset", n="+12"),
        },
        on_month_change=_store_month,
    )
    return month