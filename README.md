# 📝 Ramp Koordine Nöbet Devir Raporu

Bu proje, ramp koordinasyon vardiya devrine ait rapor formatını dijital olarak kaydetmenizi sağlar.

### Nasıl kullanılır

1. Proje dizinine girin:

   ```bash
   cd /workspaces/blank-app
   ```

2. Bağımlılıkları kurun:

   ```bash
   uv sync
   ```

3. Uygulamayı çalıştırın:

   ```bash
   uv run streamlit run streamlit_app.py
   ```

4. Açılan sayfada alanları doldurun:
   - Önceki vardiyadan devam eden uçuşlar
   - Gün içerisinde teknikte bırakılan ekipman
   - Erken çıkan personeller
   - Mesaiye kalan personeller
   - Ek hizmet takip
   - Bilgilendirme
   - Gelmeyen veya geç gelen personeller
   - Devreden / Devralan

5. `Raporu Kaydet` butonuna tıklayın.

6. Kayıtlı raporlar sayfa içinde görüntülenecektir.

### Özellikler

- Günlük vardiya raporu kaydetme
- Tarihe veya vardiyaya göre filtreleme
- Uygulama içinde son kayıtların görüntülenmesi

---

`reports.csv` dosyası aynı dizinde otomatik olarak oluşturulur.