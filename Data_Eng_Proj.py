import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
st.set_page_config(page_title="Data Engineering Project")
st.title("Elizabeth Data")
st.caption("แอปนี้ช่วยคุณตรวจสอบ จัดการ Missing Values, ประเภทข้อมูล และเตรียมข้อมูลเบื้องต้น")
file = st.file_uploader("อัปโหลดไฟล์ Excel/CSV", type=["xlsx", "csv"])#ให้ uploadfile
if file is not None: #อ่านไฟล์เป็น Data fram
    try: #กันอ่านไฟล์error กรณี  upload file อื่นที่ไม่ใช่ Excel or csv
        if file.name.lower().endswith(".csv"): #เช็คว่ามันเป็น csv หรือ excel มั้ย
            df = pd.read_csv(file,encoding="utf-8-sig") #encoding="utf-8-sig กันไม่ให้ตัวอักษรเพียน
        else:
            df = pd.read_excel(file)
        st.success(f"อัปโหลดไฟล์ {file.name} เรียบร้อยแล้ว") 
        
        #เก็บ df ล่าสุดไว้ใน session_state ตั้งแต่ต้น 
        if "df" not in st.session_state: #ตรวจสอบว่ามีตัวแปรชื่อ "df" เก็บอยู่ใน session_state แล้วหรือยัง
            st.session_state.df = df.copy() #เก็บ DataFrame (df) ที่เพิ่งอัปโหลดเข้าไปไว้ใน session_state
        df = st.session_state.df.copy()  #ทุกครั้งที่ทำการแก้อะไรต่างๆ จะเป็น df ล่าสุดที่แก้ไข
        
        #ให้เลือกว่าจะทำอะไร
        st.subheader("เลือกรายการที่ต้องการทำ")
        main_option = st.radio("กรุณาเลือกรายการที่ท่านต้องการทำ", ["ตรวจสอบและทำความสะอาดข้อมูลเบื้องต้น", "จัดการกับ Missing Value", "สร้างDummy Variableและเปลี่ยนชนิดข้อมูล"])
        
        #ถ้าเลือก Data Audit
        if main_option == "ตรวจสอบและทำความสะอาดข้อมูลเบื้องต้น":
            st.subheader("ตรวจสอบข้อมูลเบื้องต้น")
            #ตรวจสอบ Missing Value
            st.markdown("### 1) จำนวน Missing Value ในแต่ละ Column")
            miss_cnt = df.isna().sum() #เช็คว่าแต่ละ column มีจำนวนแถวที่มีค่าว่างเท่าไหร่
            audit_missing = (   #สร้างตารางแสดงผล Missing Value
                pd.DataFrame({
                    "Column Name": df.columns,
                    "Missing Count(จำนวนแถว)": miss_cnt.values,  
                    "DType": df.dtypes.astype(str).values
                })
                .sort_values("Missing Count(จำนวนแถว)", ascending=False) #เรียงลำดับให้คอลัมน์ที่ Missing เยอะสุดอยู่ข้างบน
                .reset_index(drop=True) #รีเซ็ต index ใหม่ให้เป็น 0,1,2,... ให้ดูง่าย
            )
            st.dataframe(audit_missing) #แสดงผลออกมาเป็นตาราง
                
            # ตรวจสอบ Outlier ด้วย Boxplot
            st.markdown("### 2) Outlier Check(Boxplot)")
            numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist() #เลือกเฉพาะคอลัมน์ตัวเลข
            if not numeric_cols:
                st.info("ไม่พบคอลัมน์สำหรับทำ Boxplot")
            else:
                box_col = st.selectbox("เลือกคอลัมน์เพื่อดู Boxplot", numeric_cols, key="outlier_box_col")
                fig, ax = plt.subplots(figsize=(6, 4)) #สร้าง Boxplot
                ax.boxplot(df[box_col].dropna(), vert=True, patch_artist=True) #ตัดค่าที่หายไปออกก่อน plot
                ax.set_title(f"Boxplot of {box_col}")
                ax.set_ylabel(box_col)
                st.pyplot(fig) #แสดงกราฟในหน้าเว็บ Streamlit
                #หา outlier โดยใช้ IQR
                q1 = df[box_col].quantile(0.25)
                q3 = df[box_col].quantile(0.75)
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                mask_out = (df[box_col] < lower) | (df[box_col] > upper) #ระบุว่าแถวไหนเป็น outlier
                outliers = df.loc[mask_out, box_col] #ดึงค่า outlier ของคอลัมน์นั้นออกมา
                st.write(f"พบ outlier จำนวน: **{mask_out.sum()} แถว**") #แสดงจำนวนแถวที่เป็น outlier ทั้งหมดในคอลัมน์นี้
                if not outliers.empty: # ถ้ามี outlierจะแสดงตัวอย่าง 50 แถวแรกในตาราง
                    st.dataframe(outliers.head(50).to_frame())
                    action = st.radio(
                        "เลือกวิธีจัดการกับค่า Outlier",
                        ("ลบแถวที่มีค่า Outlier ทิ้ง", "แทนที่ค่า Outlier ด้วยค่ามัธยฐาน (Median)"),
                        key="outlier_action"
                     )
                    do_process = st.button("✅ ดำเนินการกับ Outlier", disabled=(mask_out.sum() == 0))
                    if do_process:
                        df_new = df.copy()
            
                        if action == "ลบทิ้ง":
                            before = len(df_new)
                            df_new = df_new.loc[~mask_out].copy()  # เก็บเฉพาะแถวที่ไม่ใช่ outlier
                            removed = before - len(df_new)
                            st.success(f"🗑️ ลบ Outlier แล้ว {removed} แถว")
                        
                        else:  # แทนที่ด้วย median
                            median_val = float(df[box_col].median())
                            n_changed = int(mask_out.sum())
                            df_new.loc[mask_out, box_col] = median_val
                            st.success(f"🧮 แทนที่ Outlier {n_changed} ค่าในคอลัมน์ **{box_col}** ด้วย median = {median_val:g}")
            
                        # อัปเดตผลลัพธ์กลับเข้า session_state และแสดงตัวอย่าง
                        st.session_state.df = df_new.copy()
                        df = df_new  # อัปเดตตัวแปร df ในหน้านี้ด้วย (เพื่อให้วิดเจ็ตอื่นๆ ใช้ค่าล่าสุด)
                        st.dataframe(df.head(50))
                else:
                    st.info("✅ ไม่มี Outlier ในคอลัมน์นี้")
             

            #Range Check
            st.markdown("### 3) Range Check (กำหนดช่วงด้วยตนเอง)")
            if not numeric_cols:  #เช็คว่ามีคอลัมน์ตัวเลขมั้ย
                st.info("ไม่พบคอลัมน์ตัวเลขสำหรับ Range Check")
            else:
                rng_col = st.selectbox("เลือกคอลัมน์สำหรับตรวจช่วง", numeric_cols, key="range_col")
                # แปลงค่าทั้งหมดในคอลัมน์เป็นตัวเลข ถ้ามีค่าไม่ใช่ตัวเลขให้เป็น NaN (กัน error)
                current_min = float(pd.to_numeric(df[rng_col], errors="coerce").min())
                current_max = float(pd.to_numeric(df[rng_col], errors="coerce").max())
                #ให้กรอกช่วงที่ต้องการ
                c1, c2 = st.columns(2)
                with c1:
                    user_min = st.number_input("ค่าต่ำสุด", value=current_min, key="user_min")
                with c2:
                    user_max = st.number_input("ค่าสูงสุด", value=current_max, key="user_max")
                if user_min > user_max:
                    st.error("ค่าต่ำสุดต้องไม่มากกว่าค่าสูงสุด")
                else:
                    rng_mask = (df[rng_col] < user_min) | (df[rng_col] > user_max) #หาค่านอกช่วง
                    out_of_range = df[rng_mask]
                    st.write(f"ค่าที่อยู่นอกช่วง [{user_min}, {user_max}]: **{rng_mask.sum()} แถว**") #แสดงจำนวนและตัวอย่างค่านอกช่วง
                    if not out_of_range.empty:
                        st.dataframe(out_of_range[[rng_col]].head(50))
                        #ปุ่มลบค่านอกช่วง
                        if st.button(f"🗑️ ลบค่าที่อยู่นอกช่วงในคอลัมน์ {rng_col}"):
                            before = len(df) #จำนวนแถวก่อนลบ
                            df = df.loc[~rng_mask].copy() #เลือกเฉพาะแถวที่อยู่ในช่วง
                            removed = before - len(df) #จำนวนแถวที่ถูกลบ
                            st.success(f"✅ ลบข้อมูลนอกช่วงแล้ว {removed} แถว")
                            st.session_state.df = df.copy() #อัปเดต st.session_state.df
                            st.dataframe(df.head(50)) #แสดงตัวอย่างตารางหลังลบเสร็จ

        #ถ้าเลือก จัดการกับ Missing Value
        elif main_option == "จัดการกับ Missing Value":
            st.subheader("จัดการกับ Missing Value")   
            #สรุปคอลัมน์ที่มี missing
            missing_counts = df.isnull().sum() #นับจำนวนค่า missing value
            missing_cols = missing_counts[missing_counts > 0].index.tolist() #เลือกเฉพาะคอลัมน์ที่มี Missing
            if len(missing_cols) == 0:
                st.info("ไม่พบ Missing Values ในชุดข้อมูลนี้")
            else:
                st.write("จำนวน Missing ในแต่ละคอลัมน์")
                #สร้าง DataFrame สรุป Missing + dtype
                missing_df = pd.DataFrame({
                    "Column Name": missing_cols,
                    "Data Type": [df[col].dtype for col in missing_cols],
                    "Missing Count": [missing_counts[col] for col in missing_cols]
                })
                st.dataframe(missing_df)  #แสดงตารางสรุป
                #เลือกคอลัมน์ที่ต้องการจัดการ
                selected_cols = st.multiselect("เลือกคอลัมน์ที่ต้องการจัดการ Missing",options=missing_cols)
                # เพิ่มวิธีการ Clean ตาม dtype ของคอลัมน์ที่เลือก
                # วิธีที่ใช้ได้กับทุก dtype
                method_options = [
                    "เลือกวิธี...",
                    "ลบแถวที่ Missing ออกทั้งหมด (เฉพาะคอลัมน์ที่เลือก)",    
                    "เติมค่า Missing Value ด้วย Mode",
                ]
                # ถ้าคอลัมน์ที่เลือกทั้งหมดเป็น ข้อมูลเชิงปริมาณ ใช้ Mean/Median
                if selected_cols and all(np.issubdtype(df[col].dtype, np.number) for col in selected_cols):
                    method_options += [
                        "เติมค่า Missing Value ด้วย Mean",
                        "เติมค่า Missing Value ด้วย Median",
                    ]
                method = st.selectbox("เลือกวิธีจัดการ Missing", method_options)
                #ดำเนินการ
                if st.button("ดำเนินการ"):
                    if not selected_cols:   
                        st.warning("⚠️ กรุณาเลือกคอลัมน์ก่อน")
                    elif method == "เลือกวิธี...":
                        st.warning("⚠️ กรุณาเลือกวิธีจัดการ Missing ก่อน")
                    else:
                        #copy ไว้แสดงผลตอนหลังเสร็จ
                        df_before = df.copy()
                        # ดำเนินการตามวิธีที่เลือก
                        for col in selected_cols:
                            if method == "ลบแถวที่ Missing ออกทั้งหมด (เฉพาะคอลัมน์ที่เลือก)":
                                df = df.dropna(subset=[col])
                            elif method == "เติมค่า Missing Value ด้วย Mode":
                                mode_val = df[col].mode(dropna=True)
                                if len(mode_val) > 0:
                                    df[col] = df[col].fillna(mode_val.iloc[0])
                            elif method == "เติมค่า Missing Value ด้วย Mean":
                                if np.issubdtype(df[col].dtype, np.number):
                                    df[col] = df[col].fillna(df[col].mean())
                            elif method == "เติมค่า Missing Value ด้วย Median":
                                if np.issubdtype(df[col].dtype, np.number):
                                    df[col] = df[col].fillna(df[col].median())
                        st.success("✅ จัดการ Missing Values สำหรับคอลัมน์ที่เลือกเรียบร้อยแล้ว")
                        #อัปเดต session_state
                        st.session_state.df = df.copy()
                        #แสดงเฉพาะแถวที่ถูกแก้ไข/ถูกลบ 
                        if method == "ลบแถวที่ Missing ออกทั้งหมด (เฉพาะคอลัมน์ที่เลือก)":
                            removed_rows = df_before[df_before[selected_cols].isna().any(axis=1)]
                            st.header("แถวที่ถูกลบเนื่องจากมี Missing")
                            if removed_rows.empty:
                                st.info("ไม่มีแถวที่ถูกลบ")
                            else:
                                # โชว์เฉพาะคอลัมน์ที่เลือก
                                st.dataframe(removed_rows[selected_cols] if selected_cols else removed_rows)
                        else:
                            filled_mask = (df_before[selected_cols].isna()) & (df[selected_cols].notna())
                            # เลือกเฉพาะแถวที่มีการเติมอย่างน้อย 1 คอลัมน์
                            changed_idx = filled_mask.any(axis=1)
                            st.header("✏️ แถวที่ถูกแก้ไข (เติมค่า Missing แล้ว)")
                            if not changed_idx.any():
                                st.info("ไม่มีแถวที่ถูกเติมค่า Missing")
                            else:
                                # แสดงค่า ก่อน/หลัง เฉพาะคอลัมน์ที่เลือก เพื่อให้เห็นการเปลี่ยนแปลงชัดเจน
                                before_part = df_before.loc[changed_idx, selected_cols].add_suffix(" (ก่อนทำ)")
                                after_part  = df.loc[changed_idx, selected_cols].add_suffix(" (หลังทำ)")
                                diff_view = pd.concat([before_part, after_part], axis=1)
                                st.dataframe(diff_view)
                                    
        #ในส่วนของData Transform
        elif main_option == "สร้างDummy Variableและเปลี่ยนชนิดข้อมูล":
            st.subheader("รายการ")
            transform_option = st.radio(
            "กรุณาเลือกรายการที่ต้องการทำ",
            [
                "Dummy Variable",
                "เปลี่ยนชนิดข้อมูล (Data Type Conversion)"
            ]
        )
            #Dummy Variable
            if transform_option == "Dummy Variable":
                st.markdown("**🔸 สร้าง Dummy Variable**")
                # ดึงเฉพาะคอลัมน์ที่มีชนิดข้อมูลเป็น object
                object_cols = df.select_dtypes(include=['object']).columns.tolist()
                if not object_cols:
                    st.info("⚠️ ไม่พบคอลัมน์ประเภท object สำหรับสร้าง Dummy Variable")
                else:
                    col_to_encode = st.selectbox("เลือกคอลัมน์", object_cols)
                    if st.button("ดำเนินการ"):
                        # ใช้ pandas สร้าง dummy (ตัดตัวแรกออกเหมือน drop="first")
                        dummies = pd.get_dummies(df[col_to_encode], prefix=col_to_encode, drop_first=True).astype(int)
                        # ต่อคอลัมน์ dummy กลับเข้ากับ df เดิม
                        df = pd.concat([df, dummies], axis=1)
                        st.success(f"✅ทำ Dummy Variable สำหรับ {col_to_encode} เรียบร้อยแล้ว")                      
                        #อัปเดต session_state
                        st.session_state.df = df.copy()                       
                        st.dataframe(df.head()) #แสดงตาราง 5 แถวแรกของ DataFrame ที่ถูกอัปเดตแล้ว (มีคอลัมน์ dummy เพิ่ม)

            # เปลี่ยนชนิดข้อมูล (Data Type Conversion)
            elif transform_option == "เปลี่ยนชนิดข้อมูล (Data Type Conversion)":
                st.markdown("**🔸 แปลง Data Type ของคอลัมน์ที่เลือก**")

                selected_col = st.selectbox("เลือกคอลัมน์ที่ต้องการแปลง", df.columns) 
                dtype_option = st.selectbox(
                    "เลือกชนิดข้อมูลที่ต้องการแปลงเป็น",
                    ["int", "float", "string", "date", "number"]
                )
                if st.button("แปลงชนิดข้อมูล"):
                    try:
                        if dtype_option == 'int':
                            #ปรับให้ robust: coercion → ลบ inf → ใช้ Int64 รองรับ NA
                            s = pd.to_numeric(df[selected_col], errors='coerce')  # แปลง string เป็นตัวเลข, แปลงไม่ได้ = NaN
                            df[selected_col] = s.round().astype('Int64') # ใช้ dtype Int64 รองรับค่า NA ได้
                        elif dtype_option == 'float':
                            df[selected_col] = df[selected_col].astype(float)
                        elif dtype_option == 'string':
                            df[selected_col] = df[selected_col].astype(str)
                        elif dtype_option == 'date':
                            df[selected_col] = pd.to_datetime(df[selected_col], errors='coerce')
                        elif dtype_option == 'number':
                            df[selected_col] = pd.to_numeric(df[selected_col], errors='coerce')
                        st.success(f"✅ แปลง {selected_col} เป็น {dtype_option} เรียบร้อยแล้ว")                       
                        #อัปเดตsession_state
                        st.session_state.df = df.copy()
                        st.write(df[[selected_col]].head()) #แสดงตัวอย่าง 5 แถวแรกของคอลัมน์ที่แปลง
                        st.write(df[selected_col].dtypes) #แสดงชนิดข้อมูลใหม่ของคอลัมน์นั้น
                    except Exception as e:
                        st.error(f"❌ เกิดข้อผิดพลาด: {e}") #ถ้าเกิด error ขณะพยายามแปลงจะบอกข้อความ error พร้อมรายละเอียด
        #ปุ่มดาวน์โหลด
        st.markdown("---")
        st.subheader("ดาวน์โหลดผลลัพธ์")
        #ตั้งชื่อไฟล์จากชื่อไฟล์ที่อัปโหลด
        base_name = file.name.rsplit(".", 1)[0] if hasattr(file, "name") else "cleaned_data"
        data_bytes = st.session_state.df.to_csv(index=False).encode("utf-8-sig")
        fname = f"{base_name}_cleaned.csv"
        mime = "text/csv"
        st.download_button(
            "⬇️ ดาวน์โหลด",
            data=data_bytes,
            file_name=fname,
            mime=mime,
            use_container_width=True
            )      
    except Exception as e:
         st.error(f"อ่านไฟล์ไม่สำเร็จ: {e}")
else:
     st.info("⬆️ กรุณาอัปโหลดไฟล์ .xlsx หรือ .csv")










