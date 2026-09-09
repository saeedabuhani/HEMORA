from io import BytesIO
import os

from bidi.algorithm import get_display
from reportlab.graphics.shapes import Drawing, Path, PolyLine
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy import select

from . import models as m
from .security import decrypt_national_id, mask_national_id
from .services import LongitudinalTrendService, PanelCompletenessService, RecommendationEngine, TestComparisonEngine

STATUS_HE={"NORMAL":"בטווח","LOW":"נמוך","HIGH":"גבוה","CRITICAL_LOW":"קריטי נמוך","CRITICAL_HIGH":"קריטי גבוה","UNKNOWN_REFERENCE":"ללא טווח ייחוס","UNVERIFIED":"דורש אימות","INVALID":"לא תקין"}
TREND_HE={"IMPROVED":"השתפר אך עדיין חריג","WORSENED":"התרחק מהטווח","STABLE":"יציב","NEW_ABNORMALITY":"חריגה חדשה","RETURNED_TO_RANGE":"חזר לטווח","STILL_ABNORMAL":"עדיין חריג","NEW_PARAMETER":"מדד חדש","MISSING_CURRENT":"חסר בבדיקה הנוכחית","NOT_COMPARABLE":"לא ניתן להשוואה"}
SOURCE_HE={"LAB_SUPPLIED":"סופק על ידי המעבדה","LAB_CONFIG":"הגדרת המעבדה","DEMO_GENERAL":"טווח כללי להדגמה בלבד","NONE":"לא קיים"}

class ReportService:
    @staticmethod
    def _font():
        path=next((p for p in [r"C:\Windows\Fonts\arial.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"] if os.path.exists(p)),None)
        if path:
            if "HemoraHebrew" not in pdfmetrics.getRegisteredFontNames(): pdfmetrics.registerFont(TTFont("HemoraHebrew",path))
            return "HemoraHebrew"
        return "Helvetica"

    @staticmethod
    def _logo():
        drawing=Drawing(42,52)
        drop=Path(); drop.moveTo(21,51); drop.curveTo(16,40,5,29,5,17); drop.curveTo(5,6,12,1,21,1); drop.curveTo(30,1,37,6,37,17); drop.curveTo(37,29,26,40,21,51)
        drop.closePath(); drop.fillColor=colors.HexColor("#0d746f"); drop.strokeColor=None; drawing.add(drop)
        drawing.add(PolyLine([(9,18),(15,18),(18,27),(23,10),(28,23),(34,23)],strokeColor=colors.white,strokeWidth=2.2))
        return drawing

    @classmethod
    def generate_pdf(cls,db,test):
        font=cls._font(); rtl=lambda value:get_display(str(value)); output=BytesIO()
        doc=SimpleDocTemplate(output,pagesize=A4,rightMargin=34,leftMargin=34,topMargin=30,bottomMargin=34,title="HEMORA Blood Test Report",author="HEMORA")
        base=getSampleStyleSheet()["BodyText"]
        body=ParagraphStyle("he",parent=base,fontName=font,fontSize=9,leading=14,alignment=2,textColor=colors.HexColor("#132a36"),spaceAfter=4)
        small=ParagraphStyle("small",parent=body,fontSize=7.5,leading=11,textColor=colors.HexColor("#526672"))
        heading=ParagraphStyle("heading",parent=body,fontSize=16,leading=21,textColor=colors.HexColor("#0b5c59"),spaceBefore=8,spaceAfter=7)
        report_title=ParagraphStyle("report_title",parent=heading,fontSize=21,leading=27)
        brand=ParagraphStyle("brand",parent=body,fontSize=21,leading=23,textColor=colors.HexColor("#0b5c59"),alignment=2)
        brand_sub=ParagraphStyle("brand_sub",parent=small,fontSize=8,alignment=2)
        header=Table([[Paragraph("HEMORA",brand),cls._logo()],[Paragraph("Understanding change. Protecting health.",brand_sub),""]],colWidths=[480,45])
        header.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"MIDDLE"),("ALIGN",(1,0),(1,-1),"RIGHT"),("SPAN",(1,0),(1,1)),("BOTTOMPADDING",(0,0),(-1,-1),0),("TOPPADDING",(0,0),(-1,-1),0)]))
        shown_id=mask_national_id(decrypt_national_id(test.patient.national_id_encrypted))
        story=[header,Spacer(1,14),Paragraph(rtl(f"דוח בדיקת דם - {test.test_date.strftime('%d/%m/%Y')}"),report_title),Paragraph(rtl(f"מטופל: {test.patient.first_name} {test.patient.last_name}"),body),Paragraph(f"ID: {shown_id} | Accession: {test.accession_number}",small),Spacer(1,10)]

        counts={status:sum(r.status.value==status for r in test.results) for status in STATUS_HE}
        latest_run=db.scalar(select(m.AnalysisRun).where(m.AnalysisRun.blood_test_id==test.id).order_by(m.AnalysisRun.created_at.desc()))
        summary_data=[[rtl("סהכ מדדים"),rtl("בטווח"),rtl("חריגים"),rtl("קריטיים"),rtl("דורשים אימות"),rtl("איכות נתונים")],[len(test.results),counts["NORMAL"],counts["LOW"]+counts["HIGH"],counts["CRITICAL_LOW"]+counts["CRITICAL_HIGH"],counts["UNVERIFIED"],f"{latest_run.quality_score:.0f}%" if latest_run else "-"]]
        summary=Table(summary_data,colWidths=[80,75,75,75,90,85]); summary.setStyle(cls._table_style(font,header=True))
        story.extend([Paragraph(rtl("1. סיכום"),heading),summary,Paragraph(rtl("איכות הנתונים מתארת את שלמות והתאמת הנתונים לניתוח ואינה ציון בריאות."),small)])

        result_rows=[[rtl("מדד"),rtl("שם"),rtl("ערך"),rtl("טווח ייחוס"),rtl("מצב"),rtl("מקור הטווח")]]
        for r in test.results:
            low="-" if r.reference_min is None else f"{r.reference_min:g}"; high="-" if r.reference_max is None else f"{r.reference_max:g}"
            result_rows.append([r.analyte.code,rtl(r.analyte.display_name_he),f"{r.numeric_value:g} {r.unit}",f"{low} - {high}",rtl(STATUS_HE.get(r.status.value,r.status.value)),rtl(SOURCE_HE.get(r.reference_source,r.reference_source))])
        results=Table(result_rows,colWidths=[45,100,78,78,78,108],repeatRows=1); results.setStyle(cls._table_style(font,header=True))
        story.extend([Paragraph(rtl("2. תוצאות"),heading),results])

        abnormal=[r for r in test.results if r.status not in {m.ResultStatus.NORMAL,m.ResultStatus.UNKNOWN_REFERENCE}]
        abnormal_parts=[Paragraph(rtl("3. ממצאים חריגים"),heading)]
        if abnormal:
            for r in abnormal: abnormal_parts.append(Paragraph(rtl(f"{r.analyte.code} - {r.analyte.display_name_he}: {STATUS_HE.get(r.status.value,r.status.value)}. הערך נבחן מול טווח הייחוס המוצג; ממצא יחיד אינו קובע אבחנה."),body))
        else: abnormal_parts.append(Paragraph(rtl("לא נמצאו ערכים מחוץ לטווחי הייחוס שסופקו."),body))
        story.append(KeepTogether(abnormal_parts))

        previous=db.scalar(select(m.BloodTest).where(m.BloodTest.patient_id==test.patient_id,m.BloodTest.test_date<test.test_date).order_by(m.BloodTest.test_date.desc()))
        story.append(Paragraph(rtl("4. השוואה לבדיקה קודמת"),heading))
        if previous:
            comparisons=TestComparisonEngine.compare(test,previous)
            comp_rows=[[rtl("מדד"),rtl("קודם"),rtl("נוכחי"),rtl("שינוי"),rtl("אמינות")]]
            for item in comparisons:
                comp_rows.append([item["code"],str(item.get("previous","-")),str(item.get("current","-")),rtl(TREND_HE.get(item["trend"],item["trend"])),item.get("reliability","-")])
            comp=Table(comp_rows,colWidths=[60,70,70,190,90],repeatRows=1); comp.setStyle(cls._table_style(font,header=True)); story.append(comp)
        else: story.append(Paragraph(rtl("זוהי הבדיקה הראשונה במערכת ולכן עדיין אין בסיס להשוואה."),body))

        tests=db.scalars(select(m.BloodTest).where(m.BloodTest.patient_id==test.patient_id)).all(); trend=LongitudinalTrendService.calculate(tests,"HGB")
        story.append(Paragraph(rtl("5. מגמה לאורך זמן"),heading))
        if len(trend["points"])>=3:
            values=" | ".join(f'{p["date"]}: {p["value"]} {p["unit"]}' for p in trend["points"])
            story.extend([Paragraph("HGB: "+values,body),Paragraph(rtl(f"מספר תוצאות חריגות רצופות: {trend['consecutive_abnormal']}. המגמה תיאורית בלבד ואינה חיזוי עתידי."),small)])
        else: story.append(Paragraph(rtl("נדרשות לפחות שלוש בדיקות להצגת מגמה אורכית."),body))

        missing=PanelCompletenessService.evaluate(test.panel,[r.analyte.code for r in test.results]); story.append(Paragraph(rtl("6. מידע חסר"),heading))
        if missing: story.append(Paragraph(rtl(f"הפאנל שהוזן אינו כולל: {', '.join(missing)}. חסר אינו תוצאה חריגה; מומלץ לבדוק את דוח המעבדה המקורי."),body))
        else: story.append(Paragraph(rtl("לא זוהו מדדים צפויים חסרים בפאנל שהוגדר."),body))

        story.append(Paragraph(rtl("7. המלצות כלליות"),heading))
        for rec in RecommendationEngine.for_test(test): story.append(Paragraph(rtl("• "+rec["text"]),body))
        story.extend([Paragraph(rtl("8. מקורות"),heading),Paragraph("MedlinePlus - Blood Tests; NHLBI - Blood Tests; laboratory-provided documentation and reference ranges.",small),Paragraph(rtl("טווח כללי להדגמה מסומן במפורש ואינו מחליף את טווח המעבדה."),small),Paragraph(rtl("9. הצהרה רפואית"),heading),Paragraph(rtl("HEMORA היא מערכת תומכת מידע ואינה מהווה אבחנה רפואית, ייעוץ רפואי או תחליף לבדיקה ולהחלטה של איש מקצוע רפואי. טווחי ייחוס עשויים להשתנות בין מעבדות ובין מטופלים."),body),Paragraph("Algorithm: HEMORA-CLINICAL-1.0.0",small)])
        doc.build(story); return output.getvalue()

    @staticmethod
    def _table_style(font,header=False):
        rules=[("FONTNAME",(0,0),(-1,-1),font),("FONTSIZE",(0,0),(-1,-1),7.5),("GRID",(0,0),(-1,-1),.3,colors.HexColor("#cbd5e1")),("ALIGN",(0,0),(-1,-1),"RIGHT"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f8fafc")]),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]
        if header: rules.extend([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#d8f1ee")),("TEXTCOLOR",(0,0),(-1,0),colors.HexColor("#0b5c59"))])
        return TableStyle(rules)
