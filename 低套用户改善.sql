3.低套用户改善

DROP TABLE n_cjy_200217_ditao_01 ; 
CREATE TABLE n_cjy_200217_ditao_01  AS 
select /*+ parallel(8) use_hash(t,t1,t2) */ 
               t.user_id,t.INNET_DATE,SUM(t2.flow_cost) package_fee 
          FROM bsdata.v_md_per_inf_attribute_day_02 t,
               bsdata.v_md_user_prod_package_day_02 t1,
               bsdata.v_cjy_cfg_flow_package t2
         where t.day_number = to_char(sysdate-1,'dd')
           AND t.user_id = t1.user_id
           AND t.user_status < 19
           AND t1.day_number = to_char(sysdate-1,'dd')
           and t1.start_date <= to_char(add_months(trunc(sysdate-1,'mm'),+1),'yyyymmdd')   ------------------
           AND nvl(t1.end_date,21001231) > to_char(last_day(sysdate-1),'yyyymmdd') -------------------
           AND t1.prodid = to_char(t2.package_code)
           AND (t2.package_attri = 1 or t2.package_code = 2000012882)
           AND t2.is_current = 1  
         group by t.user_id,t.INNET_DATE
   ;


DROP TABLE n_cjy_200217_rzk_01; 
CREATE TABLE n_cjy_200217_rzk_01
AS 
select /*+ parallel(8) use_hash(t,t1,t2) */ 
       t.*,
       nvl(t2.fee,0) fee_rz 
  from (SELECT /*+ parallel(8) use_hash(t) */ 
               DISTINCT t1.user_id
          from bsdata.v_md_per_inf_attribute_day_02 t1,
               bsdata.v_md_user_prod_package_day_02 t2
         where t2.PRODID in  ('2000011752','2000007712','2000009707','2000009784','2000009781','2000007711','2000009731','2000007942',
           '2000009728','2000009618','2000009587','2000009615','2000009706','2000009796','2000009709','2000009586','
           2000009818','2000009727','2000012931')
           AND t2.day_number = to_char(sysdate-1,'dd')
           AND t2.start_date <= to_char(last_day(sysdate-1),'yyyymmdd')---------
           AND t2.end_date >= to_char(last_day(sysdate-1),'yyyymmdd')   --------------
           AND t1.user_id = t2.user_id
           AND t1.day_number = to_char(sysdate-1,'dd')
           AND t1.user_status < 19
       ) t,
       (select /*+ parallel(8) use_hash(t) */ 
               t.user_id,sum(t.fee_consume) fee
          from bsdata.v_user_account_bill_day_02 t
         WHERE t.day_number <= to_char(sysdate-1,'dd')
           AND t.fee_item IN ('PZii1','PZiy1','PZiy2','PZii2')
          GROUP by t.user_id
       ) t2
 WHERE  t.user_id = t2.user_id(+)
   ;



DROP TABLE n_cjy_200217_ditao_02 ; 
CREATE TABLE n_cjy_200217_ditao_02  AS 
SELECT /*+ parallel(t,8) parallel(t2,8) parallel(t3,8) parallel(t4,8) parallel(t5,8) parallel(t6,8) use_hash(t,t2,t3,t4,t5,t6) */ 
t.user_id,nvl(t3.package_fee,0) package_fee,
case when t4.user_id is not null then 1 else 0 end is_rz,
nvl(t4.fee_rz,0) fee_rz,
CASE WHEN t5.USER_ID_FUHAO IS NOT NULL THEN 1 ELSE 0 END is_fuka,
nvl(t6.GPRS001_10,0)/1024/1024 dou
FROM
bsdata.v_md_per_inf_attribute_day_02 t,
n_cjy_200217_ditao_01 t3,
n_cjy_200217_rzk_01 t4,
(SELECT  /*+ parallel(t,8) */  distinct t.USER_ID_FUHAO FROM  bsdata.v_ysl_190425_zdfh t)  t5,----------------该视图来自之前上线的全量用户融合率处理过程中的一步，取多终端共享主副号
bsdata.v_subview_gprs_day_02 t6
where t.user_id = t3.user_id(+)
and   t.user_id = t4.user_id(+)
and   t.user_id = t5.USER_ID_FUHAO(+)
and   t.user_id = t6.user_id(+)
and   t.day_number = to_char(sysdate-1,'dd')
and   t.user_status < 19
and   t6.day_number(+) = to_char(sysdate-1,'dd')
and   t6.DATA_TYPE(+) = 2
;



------------出数据----------------
select /*+ parallel(t,8) parallel(t2,8) parallel(t3,8) use_hash(t,t2,t3) */  
decode(substr(t.user_id,1,2),14,'南京',11,'苏州',19,'无锡',17,'常州',20,'南通',18,'镇江',23,'扬州',21,'泰州',16,'徐州',22,'盐城',12,'淮安',15,'连云港',13,'宿迁') city_name, 
count( t.user_id ),--------------拍照前月底收费低套
count(case when  nvl(t3.package_fee,0)>= 30 and t3.is_rz = 0 and t3.is_fuka = 0 then  t.user_id end)----------其中当月迁出
from 
n_cjy_200217_ditao_last t,-------------------以每月最后一天的n_cjy_200217_ditao_02表全量数据备份
bsdata.V_USER_FEE_ADD_day_01 t2,
n_cjy_200217_ditao_02 t3
where t.user_id = t2.USER_ID
and   t.user_id = t3.user_id(+)
and   t2.DAY_NUMBER = to_char(last_day(add_months(sysdate-1,-1)),'dd')
and   t.package_fee < 30 
and   t.is_rz = 0 
and   t.is_fuka = 0
GROUP BY cube(substr(t.user_id,1,2))
ORDER BY decode(substr(t.user_id,1,2),14,1,11,2,19,3,17,4,20,5,18,6,23,7,21,8,16,9,22,10,12,11,15,12,13,13) 
;

select /*+ parallel(t,8) parallel(t2,8) use_hash(t,t2) */  
decode(substr(t.user_id,1,2),14,'南京',11,'苏州',19,'无锡',17,'常州',20,'南通',18,'镇江',23,'扬州',21,'泰州',16,'徐州',22,'盐城',12,'淮安',15,'连云港',13,'宿迁') city_name, 
count(case when  (nvl(t3.package_fee,0)>= 30 and t3.is_rz = 0 and t3.is_fuka = 0） OR T3.USER_ID IS NULL  then  t.user_id end)------------其中当月迁入
from 
n_cjy_200217_ditao_02 t,
bsdata.V_USER_FEE_ADD_day_02 t2,
n_cjy_200217_ditao_last t3
where t.user_id = t2.USER_ID
and   t.user_id = t3.user_id(+)
and   t2.DAY_NUMBER = to_char(sysdate-1,'dd')
and   t.package_fee < 30 
and   t.is_rz = 0 
and   t.is_fuka = 0
GROUP BY cube(substr(t.user_id,1,2))
ORDER BY decode(substr(t.user_id,1,2),14,1,11,2,19,3,17,4,20,5,18,6,23,7,21,8,16,9,22,10,12,11,15,12,13,13) 
;



select /*+ parallel(t,8) parallel(t2,8) use_hash(t,t2) */  
decode(substr(t.user_id,1,2),14,'南京',11,'苏州',19,'无锡',17,'常州',20,'南通',18,'镇江',23,'扬州',21,'泰州',16,'徐州',22,'盐城',12,'淮安',15,'连云港',13,'宿迁') city_name, 
count(t.user_id),----------------副卡用户数
count(case when t.dou >= 1024 then t.user_id end)/count(t.user_id)------------------当月大于1G占比
from 
n_cjy_200217_ditao_02 t
where t.is_rz = 0 
and   t.is_fuka = 1
GROUP BY cube(substr(t.user_id,1,2))
ORDER BY decode(substr(t.user_id,1,2),14,1,11,2,19,3,17,4,20,5,18,6,23,7,21,8,16,9,22,10,12,11,15,12,13,13) 
;


select /*+ parallel(t,8) parallel(t2,8) use_hash(t,t2) */  
decode(substr(t.user_id,1,2),14,'南京',11,'苏州',19,'无锡',17,'常州',20,'南通',18,'镇江',23,'扬州',21,'泰州',16,'徐州',22,'盐城',12,'淮安',15,'连云港',13,'宿迁') city_name, 
count(t.user_id),-------------------日租卡用户数
count(case when t.fee_rz < 5 then t.user_id end)------------日租费低于5元用户数
from 
n_cjy_200217_ditao_02 t,
bsdata.V_USER_FEE_ADD_day_02 t2
where t.user_id = t2.USER_ID
and   t2.DAY_NUMBER = to_char(sysdate-1,'dd')
and   t.is_rz = 1 
and   t.is_fuka = 0
GROUP BY cube(substr(t.user_id,1,2))
ORDER BY decode(substr(t.user_id,1,2),14,1,11,2,19,3,17,4,20,5,18,6,23,7,21,8,16,9,22,10,12,11,15,12,13,13) 
;
