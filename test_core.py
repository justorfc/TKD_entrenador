"""Pruebas reproducibles: python -m unittest -v test_core.py.

Los datos son ficticios y no constituyen ejemplos de prescripción para menores.
"""
from datetime import date, timedelta
from pathlib import Path
import sqlite3
import tempfile
import unittest
from core import (Store, age_on, adult_hr, manual_pulse, orthostatic_risk, number,
                  distribute, build_week, composition, report_html, export_sessions)
from historical import HISTORICAL


class Calculations(unittest.TestCase):
    def test_manual_conversion(self):
        self.assertEqual(manual_pulse(15,6),150)
        self.assertEqual(manual_pulse(16,6)-manual_pulse(15,6),10)

    def test_orthostatic_risk(self):
        below=orthostatic_risk(60,74)
        self.assertEqual(below['difference'],14);self.assertFalse(below['risk'])
        above=orthostatic_risk(60,76)
        self.assertEqual(above['difference'],16);self.assertTrue(above['risk'])
        boundary=orthostatic_risk(60,75)
        self.assertFalse(boundary['risk'])

    def test_age_birthday(self):
        self.assertEqual(age_on('2008-10-27','2026-10-26'),17)
        self.assertEqual(age_on('2008-10-27','2026-10-27'),18)

    def test_tanaka_and_karvonen(self):
        r=adult_hr('1999-01-01','2026-10-26',64,70)
        self.assertAlmostEqual(r['maximum'],189.1)
        self.assertAlmostEqual(r['target'],151.57)
        self.assertAlmostEqual(adult_hr('1999-01-01','2026-10-26',64,70,193)['target'],154.3)

    def test_minor_rejected(self):
        with self.assertRaises(ValueError):
            adult_hr('2012-01-01','2026-10-26',64,70)

    def test_invalid_numbers(self):
        for value in ('NaN','inf','-3',''):
            with self.subTest(value=value),self.assertRaises(ValueError):
                number(value,'dato')
        self.assertEqual(number('12,5','dato'),12.5)

    def test_integer_allocation(self):
        self.assertEqual(distribute(7,3,True),[3,2,2])
        self.assertEqual(sum(distribute(1.92,3,True)),2)
        self.assertAlmostEqual(sum(distribute(34.2,5)),34.2)

    def test_invalid_maximum(self):
        with self.assertRaises(ValueError):
            adult_hr('1999-01-01','2026-10-26',200,70,190)

    def test_history_complete(self):
        self.assertEqual(set(HISTORICAL),{'EFG','EFE','EFC'})
        for rows in HISTORICAL.values():
            self.assertEqual([x['week'] for x in rows],list(range(1,49)))
        self.assertEqual(HISTORICAL['EFC'][40]['volume'],97)
        self.assertEqual(HISTORICAL['EFC'][40]['intensity'],0)


class Storage(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.path=Path(self.temp.name)
        self.s=Store(self.path/'data.sqlite3')
        self.a=self.s.add_athlete('Persona ficticia','1999-01-01','Masculino')
        self.monday=(date.today()-timedelta(days=date.today().weekday()+7)).isoformat()
        self.s.save_ref(self.a,'Cross','General','minutos',90)
        self.s.save_ref(self.a,'Patadas','Especial','repeticiones',200,20)
        self.s.save_ref(self.a,'Combate','Competitiva','asaltos',16,round_minutes=3)

    def tearDown(self):
        self.s.db.close();self.temp.cleanup()

    def plan(self):
        return self.s.create_plan(self.a,self.monday,'Preparación general',[0,2,4],{'General':50,'Especial':50,'Competitiva':50},'Prueba de software, no prescripción')

    def session(self,pid=None,**kwargs):
        data=dict(duration=60,rpe=5,coach_rpe=4,rpe_delay=30,general_min=20,special_min=10,competitive_min=5,actual_work='Registro ficticio')
        data.update(kwargs)
        return self.s.add_session(self.a,self.monday,plan_id=pid,**data)

    def test_week_units_and_totals(self):
        pid=self.plan();items=self.s.rows('SELECT * FROM items WHERE plan_id=?',(pid,))
        q={c:sum(x['quantity'] for x in items if x['category']==c) for c in ('General','Especial','Competitiva')}
        self.assertEqual(q,{'General':45,'Especial':100,'Competitiva':8})
        comp=composition(items)
        self.assertEqual(comp['Competitiva'][0],24)
        self.assertAlmostEqual(sum(x[1] for x in comp.values()),100)

    def test_zero_reference_percentage_omits_work(self):
        refs=self.s.rows('SELECT * FROM refs WHERE athlete_id=?',(self.a,))
        items=build_week(refs,self.monday,[0,2],{'General':0,'Especial':50,'Competitiva':0})
        self.assertTrue(all(x['category']=='Especial' for x in items))
        with self.assertRaises(ValueError):
            build_week(refs,self.monday,[0],dict.fromkeys(('General','Especial','Competitiva'),0))

    def test_snapshot_independent_of_later_reference(self):
        pid=self.plan()
        self.s.save_ref(self.a,'Cross','General','minutos',10)
        total=self.s.db.execute("SELECT SUM(quantity) FROM items WHERE plan_id=? AND exercise='Cross'",(pid,)).fetchone()[0]
        self.assertEqual(total,45)

    def test_plan_freeze(self):
        pid=self.plan();iid=self.s.rows('SELECT id FROM items WHERE plan_id=?',(pid,))[0]['id']
        self.s.edit_item(iid,self.monday,12,12,90,'Cambiar',target_rpe=4)
        self.s.review_plan(pid,'Entrenador ficticio')
        with self.assertRaises(ValueError):
            self.s.edit_item(iid,self.monday,10,10,60,'No permitido')
        with self.assertRaises(ValueError):
            self.s.remove_item(iid)

    def test_session_load(self):
        pid=self.plan();self.s.review_plan(pid,'Prueba');sid=self.session(pid)
        self.assertEqual(self.s.rows('SELECT duration*rpe AS n FROM sessions WHERE id=?',(sid,))[0]['n'],300)

    def test_draft_cannot_be_recorded_as_reviewed(self):
        with self.assertRaises(ValueError):
            self.session(self.plan())

    def test_session_active_minutes_validation(self):
        with self.assertRaises(ValueError):
            self.session(general_min=100)

    def test_session_requires_real_date(self):
        with self.assertRaises(ValueError):
            self.s.add_session(self.a,(date.today()+timedelta(days=1)).isoformat(),60,5,4,30,20,10,5,'Prueba')

    def test_recovery_delay_required(self):
        with self.assertRaises(ValueError):
            self.s.add_measurement(self.a,self.monday,'FC recuperación (lpm)',130,'Oxímetro')
        self.s.add_measurement(self.a,self.monday,'FC recuperación (lpm)',130,'Oxímetro',30)

    def test_backup_restore(self):
        self.plan();copy=self.path/'backup.sqlite3';self.s.backup(copy)
        self.s.add_athlete('Temporal','2000-01-01','Sin registrar')
        prior=self.s.restore(copy)
        self.assertTrue(prior.exists())
        self.assertEqual(len(self.s.rows('SELECT * FROM athletes')),1)
        self.assertEqual(len(self.s.rows('SELECT * FROM plans')),1)

    def test_bad_backup_preserves_data(self):
        bad=self.path/'bad.sqlite3'
        db=sqlite3.connect(bad)
        try:
            with db:
                db.execute('PRAGMA user_version=1')
        finally:
            db.close()
        with self.assertRaises(ValueError):
            self.s.restore(bad)
        self.assertEqual(self.s.athlete(self.a)['name'],'Persona ficticia')

    def test_void_and_escape(self):
        sid=self.session(actual_work='<script>alert(1)</script>')
        report=report_html(self.s,self.a)
        self.assertNotIn('<script>',report);self.assertIn('&lt;script&gt;',report)
        self.s.void_record('sessions',sid,'Corrección')
        self.assertNotIn('alert(1)',report_html(self.s,self.a))
        self.assertEqual(self.s.rows('SELECT void FROM sessions')[0]['void'],1)

    def test_csv_formula_escape(self):
        self.session(actual_work='=1+1');path=self.path/'export.csv';export_sessions(self.s,self.a,path)
        self.assertIn("'=1+1",path.read_text(encoding='utf-8-sig'))

    def test_invalid_weekday(self):
        refs=self.s.rows('SELECT * FROM refs')
        tuesday=(date.fromisoformat(self.monday)+timedelta(days=1)).isoformat()
        with self.assertRaises(ValueError):
            build_week(refs,tuesday,[0],dict.fromkeys(('General','Especial','Competitiva'),50))

    def test_foreign_athlete_link_rejected(self):
        pid=self.plan();self.s.review_plan(pid,'Prueba')
        other=self.s.add_athlete('Otro','2001-01-01','Sin registrar')
        with self.assertRaises(ValueError):
            self.s.add_session(other,self.monday,60,5,4,30,20,10,5,'Prueba',plan_id=pid)


if __name__=='__main__':
    unittest.main()
