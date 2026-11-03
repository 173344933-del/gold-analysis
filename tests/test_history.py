import unittest
from datetime import date,timedelta
from unittest.mock import patch
from radar import history

class HistoricalTests(unittest.TestCase):
 def rows(self,n=350):
  return [{'date':str(date(2020,1,1)+timedelta(days=i)),'close':100+i,'volume':1000} for i in range(n)]
 def test_daily_entry_is_strictly_after_event(self):
  with patch('radar.history.series',return_value=({'frequency':'daily','adjustment':'index'},self.rows())):
   r=history.study('test','2020-01-10')
  self.assertEqual(r['entry_date'],'2020-01-11');self.assertEqual(r['returns']['1'],round((111/110-1)*100,2))
 def test_monthly_average_never_becomes_daily_event_return(self):
  rows=[{'date':'2020-01-31','close':100},{'date':'2020-02-29','close':110},{'date':'2020-03-31','close':121}]
  with patch('radar.history.series',return_value=({'frequency':'monthly_average','adjustment':'monthly'},rows)):
   r=history.study('test','2020-01-10')
  self.assertEqual(r['entry_date'],'2020-02-29');self.assertEqual(r['unit'],'月度观测');self.assertEqual(r['returns']['1'],10)
 def test_incomplete_windows_are_null_not_zero(self):
  with patch('radar.history.series',return_value=({'frequency':'daily','adjustment':'index'},self.rows(20))):
   r=history.study('test','2020-01-10')
  self.assertIsNone(r['returns']['20']);self.assertIsNone(r['drawdown'])
 def test_pre_listing_event_not_forward_filled(self):
  with patch('radar.history.series',return_value=({'frequency':'daily','adjustment':'index'},self.rows())):
   self.assertFalse(history.study('test','2019-01-01')['available'])
 def test_drawdown_is_peak_to_trough(self):self.assertEqual(history.drawdown([100,120,90,110]),-25)
 def test_unadjusted_split_window_not_treated_as_investment_loss(self):
  rows=self.rows()
  for r in rows[15:]:r['close']/=2
  with patch('radar.history.series',return_value=({'frequency':'daily','adjustment':'未复权'},rows)):
   r=history.study('test','2020-01-10')
  self.assertTrue(r['corporate_action_warning']);self.assertIsNone(r['returns']['20']);self.assertIsNone(r['drawdown']);self.assertIsNotNone(r['returns']['1'])
 def test_signal_conditions_do_not_look_into_future(self):
  rows=self.rows();rows[100]['close']=400
  meta={'frequency':'daily','adjustment':'index'}
  history.signals.cache_clear()
  with patch('radar.history.series',return_value=(meta,rows)):
   full=history.signals('test')
  history.signals.cache_clear()
  with patch('radar.history.series',return_value=(meta,rows[:200])):
   short=history.signals('test')
  relevant=lambda xs:[(r['date'],r['kind'],r['price'],r['rule']) for r in xs if r['date']<=rows[199]['date']]
  self.assertEqual(relevant(full),relevant(short));history.signals.cache_clear()
 def test_actual_series_integrity_and_unique_dates(self):
  for meta in history.manifest()['series']:
   _,rows=history.series(meta['symbol'])
   self.assertEqual(len(rows),meta['count']);self.assertEqual(rows[0]['date'],meta['first']);self.assertEqual(rows[-1]['date'],meta['last'])
   self.assertEqual(len({r['date'] for r in rows}),len(rows));self.assertTrue(all(r['close']>0 for r in rows))
 def test_hindsight_labels_are_explicit(self):
  labels=[e for e in history.EVENTS if e[6] and e[5]=='hindsight']
  self.assertGreaterEqual(len(labels),3)

if __name__=='__main__':unittest.main()
