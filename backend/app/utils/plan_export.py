"""
プランエクスポート機能
PDF、カレンダー、画像形式での出力
"""
import json
from datetime import datetime, timedelta
from typing import Dict, Any
from io import BytesIO

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from icalendar import Calendar, Event
    ICAL_AVAILABLE = True
except ImportError:
    ICAL_AVAILABLE = False

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


def export_to_pdf(plan: Dict[str, Any]) -> BytesIO:
    """プランをPDF形式で出力"""
    if not REPORTLAB_AVAILABLE:
        raise ImportError("reportlabがインストールされていません。pip install reportlabでインストールしてください。")
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    story = []
    styles = getSampleStyleSheet()
    
    # タイトル
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1f77b4'),
        spaceAfter=30,
    )
    story.append(Paragraph(plan.get("title", "旅行プラン"), title_style))
    story.append(Spacer(1, 12))
    
    # 概要
    if plan.get("summary"):
        story.append(Paragraph(f"<b>概要:</b> {plan['summary']}", styles['Normal']))
        story.append(Spacer(1, 12))
    
    # SatoTrip-AI のプラン形式（spots配列）に対応
    if "spots" in plan:
        # spots配列を日別にグループ化
        days_dict = {}
        for spot in plan.get("spots", []):
            day = spot.get("day", 1)
            if day not in days_dict:
                days_dict[day] = []
            days_dict[day].append(spot)
        
        # 各日のスケジュール
        for day in sorted(days_dict.keys()):
            day_spots = days_dict[day]
            
            # 日見出し
            day_style = ParagraphStyle(
                'DayTitle',
                parent=styles['Heading2'],
                fontSize=18,
                textColor=colors.HexColor('#ff7f0e'),
                spaceAfter=12,
            )
            story.append(Paragraph(f"{day}日目", day_style))
            story.append(Spacer(1, 12))
            
            # スケジュール表
            schedule_data = [["時刻", "スポット名", "説明", "滞在時間"]]
            for spot_data in day_spots:
                spot_info = spot_data.get("spot", {}) if isinstance(spot_data.get("spot"), dict) else {}
                schedule_data.append([
                    spot_data.get("startTime", ""),
                    spot_info.get("name", spot_data.get("name", "")),
                    spot_data.get("description", spot_info.get("description", ""))[:50],
                    f"{spot_info.get('durationMinutes', 60)}分",
                ])
            
            table = Table(schedule_data, colWidths=[30*mm, 50*mm, 60*mm, 20*mm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(table)
            story.append(PageBreak())
    # SatoTrip のプラン形式（days配列）に対応
    elif "days" in plan:
        for day_data in plan.get("days", []):
            day_num = day_data.get("day", 0)
            theme = day_data.get("theme", "")
            
            # 日見出し
            day_style = ParagraphStyle(
                'DayTitle',
                parent=styles['Heading2'],
                fontSize=18,
                textColor=colors.HexColor('#ff7f0e'),
                spaceAfter=12,
            )
            story.append(Paragraph(f"{day_num}日目: {theme}", day_style))
            story.append(Spacer(1, 12))
            
            # スケジュール表
            schedule_data = [["時刻", "活動", "場所", "時間"]]
            for item in day_data.get("schedule", []):
                schedule_data.append([
                    item.get("time", ""),
                    item.get("activity", ""),
                    item.get("place", ""),
                    item.get("duration", ""),
                ])
            
            table = Table(schedule_data, colWidths=[30*mm, 50*mm, 60*mm, 20*mm])
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            story.append(table)
            story.append(PageBreak())
    
    # アドバイス
    if plan.get("tips"):
        story.append(Paragraph("<b>プランのアドバイス</b>", styles['Heading2']))
        story.append(Spacer(1, 12))
        for tip in plan["tips"]:
            story.append(Paragraph(f"• {tip}", styles['Normal']))
            story.append(Spacer(1, 6))
    
    doc.build(story)
    buffer.seek(0)
    return buffer


def export_to_ical(plan: Dict[str, Any], start_date: datetime = None) -> bytes:
    """プランをiCal形式で出力"""
    if not ICAL_AVAILABLE:
        raise ImportError("icalendarがインストールされていません。pip install icalendarでインストールしてください。")
    
    if start_date is None:
        start_date = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    
    cal = Calendar()
    cal.add('prodid', '-//SatoTrip Travel Plan//EN')
    cal.add('version', '2.0')
    
    current_date = start_date
    
    # SatoTrip-AI のプラン形式（spots配列）に対応
    if "spots" in plan:
        days_dict = {}
        for spot in plan.get("spots", []):
            day = spot.get("day", 1)
            if day not in days_dict:
                days_dict[day] = []
            days_dict[day].append(spot)
        
        for day in sorted(days_dict.keys()):
            day_spots = days_dict[day]
            event_date = current_date + timedelta(days=day - 1)
            
            for spot_data in day_spots:
                time_str = spot_data.get("startTime", "09:00")
                try:
                    hour, minute = map(int, time_str.split(":"))
                    event_time = event_date.replace(hour=hour, minute=minute)
                except:
                    event_time = event_date.replace(hour=9, minute=0)
                
                spot_info = spot_data.get("spot", {}) if isinstance(spot_data.get("spot"), dict) else {}
                spot_name = spot_info.get("name", spot_data.get("name", ""))
                duration_minutes = spot_info.get("durationMinutes", 60)
                
                event = Event()
                event.add('summary', spot_name)
                event.add('dtstart', event_time)
                event.add('dtend', event_time + timedelta(minutes=duration_minutes))
                event.add('description', spot_data.get("description", spot_info.get("description", "")))
                event.add('location', spot_info.get("area", ""))
                cal.add_component(event)
    # SatoTrip のプラン形式（days配列）に対応
    elif "days" in plan:
        for day_data in plan.get("days", []):
            day_start = current_date.replace(hour=9, minute=0)
            
            for item in day_data.get("schedule", []):
                time_str = item.get("time", "09:00")
                try:
                    hour, minute = map(int, time_str.split(":"))
                    event_time = current_date.replace(hour=hour, minute=minute)
                except:
                    event_time = day_start
                
                duration_str = item.get("duration", "1時間")
                duration_hours = 1
                if "時間" in duration_str:
                    try:
                        duration_hours = int(duration_str.replace("時間", "").strip())
                    except:
                        pass
                
                event = Event()
                event.add('summary', f"{item.get('activity', '活動')} - {item.get('place', '')}")
                event.add('dtstart', event_time)
                event.add('dtend', event_time + timedelta(hours=duration_hours))
                event.add('description', item.get("description", ""))
                event.add('location', item.get("place", ""))
                cal.add_component(event)
            
            current_date += timedelta(days=1)
    
    return cal.to_ical()


def export_to_image(plan: Dict[str, Any]) -> BytesIO:
    """プランを画像形式で出力（簡易版）"""
    if not PIL_AVAILABLE:
        raise ImportError("Pillowがインストールされていません。pip install Pillowでインストールしてください。")
    
    # 簡易的な画像生成
    img = Image.new('RGB', (800, 1200), color='white')
    draw = ImageDraw.Draw(img)
    
    try:
        font_large = ImageFont.truetype("arial.ttf", 24)
        font_normal = ImageFont.truetype("arial.ttf", 16)
    except:
        font_large = ImageFont.load_default()
        font_normal = ImageFont.load_default()
    
    y = 30
    draw.text((50, y), plan.get("title", "旅行プラン"), fill='black', font=font_large)
    y += 50
    
    # SatoTrip-AI のプラン形式に対応
    if "spots" in plan:
        days_dict = {}
        for spot in plan.get("spots", []):
            day = spot.get("day", 1)
            if day not in days_dict:
                days_dict[day] = []
            days_dict[day].append(spot)
        
        for day in sorted(days_dict.keys()):
            day_text = f"{day}日目"
            draw.text((50, y), day_text, fill='blue', font=font_normal)
            y += 30
            
            for spot_data in days_dict[day][:5]:  # 最初の5項目のみ
                spot_info = spot_data.get("spot", {}) if isinstance(spot_data.get("spot"), dict) else {}
                spot_name = spot_info.get("name", spot_data.get("name", ""))
                item_text = f"  {spot_data.get('startTime', '')} - {spot_name}"
                draw.text((70, y), item_text, fill='black', font=font_normal)
                y += 25
            
            y += 20
    # SatoTrip のプラン形式に対応
    elif "days" in plan:
        for day_data in plan.get("days", []):
            day_text = f"{day_data.get('day', 0)}日目: {day_data.get('theme', '')}"
            draw.text((50, y), day_text, fill='blue', font=font_normal)
            y += 30
            
            for item in day_data.get("schedule", [])[:5]:  # 最初の5項目のみ
                item_text = f"  {item.get('time', '')} - {item.get('activity', '')} @ {item.get('place', '')}"
                draw.text((70, y), item_text, fill='black', font=font_normal)
                y += 25
            
            y += 20
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    return buffer

