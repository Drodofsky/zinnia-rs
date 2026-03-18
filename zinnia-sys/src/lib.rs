use std::ffi::c_char;

#[repr(C)]
pub struct zinnia_recognizer_t {
    _private: [u8; 0],
}

#[repr(C)]
pub struct zinnia_character_t {
    _private: [u8; 0],
}
#[repr(C)]
pub struct zinnia_result_t {
    _private: [u8; 0],
}

unsafe extern "C" {
    pub fn zinnia_recognizer_new() -> *mut zinnia_recognizer_t;
    pub fn zinnia_recognizer_destroy(recognizer: *mut zinnia_recognizer_t);

    pub fn zinnia_recognizer_open(
        recognizer: *mut zinnia_recognizer_t,
        filename: *const c_char,
    ) -> i32;

    pub fn zinnia_character_new() -> *mut zinnia_character_t;
    pub fn zinnia_character_destroy(character: *mut zinnia_character_t);

    pub fn zinnia_character_set_width(character: *mut zinnia_character_t, width: usize);
    pub fn zinnia_character_set_height(character: *mut zinnia_character_t, height: usize);
    pub fn zinnia_character_clear(character: *mut zinnia_character_t);
    pub fn zinnia_character_strerror(character: *mut zinnia_character_t) -> *const c_char;
    pub fn zinnia_character_add(
        character: *mut zinnia_character_t,
        id: usize,
        x: i32,
        y: i32,
    ) -> i32;

    pub fn zinnia_result_size(result: *mut zinnia_result_t) -> usize;
    pub fn zinnia_result_value(result: *mut zinnia_result_t, i: usize) -> *const c_char;
    pub fn zinnia_result_score(result: *mut zinnia_result_t, i: usize) -> f32;
    pub fn zinnia_result_destroy(result: *mut zinnia_result_t);
    pub fn zinnia_recognizer_classify(
        recognizer: *mut zinnia_recognizer_t,
        character: *const zinnia_character_t,
        nbest: usize,
    ) -> *mut zinnia_result_t;
    pub fn zinnia_recognizer_strerror(recognizer: *mut zinnia_recognizer_t) -> *const c_char;
}

#[cfg(test)]
mod tests {
    use std::ffi::{CStr, CString};

    use super::*;

    #[test]
    fn recognizer_can_be_created_and_destroyed() {
        let ptr = unsafe { zinnia_recognizer_new() };
        assert!(!ptr.is_null());

        unsafe {
            zinnia_recognizer_destroy(ptr);
        }
    }
    #[test]
    fn recognizer_open_nonexistent_model_fails_with_error() {
        let ptr = unsafe { zinnia_recognizer_new() };
        assert!(!ptr.is_null());

        let path = CString::new("/definitely/not/found.model").unwrap();
        let ok = unsafe { zinnia_recognizer_open(ptr, path.as_ptr()) };
        assert_eq!(ok, 0);

        let err = unsafe { zinnia_recognizer_strerror(ptr) };
        assert!(!err.is_null());

        let err_str = unsafe { CStr::from_ptr(err) }.to_string_lossy();
        assert!(!err_str.is_empty());

        unsafe {
            zinnia_recognizer_destroy(ptr);
        }
    }
    #[test]
    fn classify_empty_character_does_not_crash() {
        let rec = unsafe { zinnia_recognizer_new() };
        assert!(!rec.is_null());

        // this will fail, but that's fine for now
        let path = CString::new("/definitely/not/found.model").unwrap();
        unsafe { zinnia_recognizer_open(rec, path.as_ptr()) };

        let ch = unsafe { zinnia_character_new() };
        assert!(!ch.is_null());

        unsafe {
            zinnia_character_set_width(ch, 100);
            zinnia_character_set_height(ch, 100);

            let result = zinnia_recognizer_classify(rec, ch, 10);

            // may be null since model isn't loaded
            if !result.is_null() {
                zinnia_result_destroy(result);
            }

            zinnia_character_destroy(ch);
            zinnia_recognizer_destroy(rec);
        }
    }
    #[test]
    fn classify_simple_stroke() {
        let rec = unsafe { zinnia_recognizer_new() };
        assert!(!rec.is_null());

        let model = "../model/handwriting-ja.model\0";
        let ok = unsafe { zinnia_recognizer_open(rec, model.as_ptr() as *const i8) };
        if ok == 0 {
            let err = unsafe { zinnia_recognizer_strerror(rec) };
            let msg = if err.is_null() {
                "<null>".into()
            } else {
                unsafe { CStr::from_ptr(err) }
                    .to_string_lossy()
                    .into_owned()
            };
            panic!("failed to open model: {msg}");
        }

        let ch = unsafe { zinnia_character_new() };
        assert!(!ch.is_null());

        unsafe {
            zinnia_character_set_width(ch, 300);
            zinnia_character_set_height(ch, 300);

            // one simple stroke
            assert_eq!(zinnia_character_add(ch, 0, 50, 150), 1);
            assert_eq!(zinnia_character_add(ch, 0, 120, 150), 1);
            assert_eq!(zinnia_character_add(ch, 0, 190, 150), 1);
            assert_eq!(zinnia_character_add(ch, 0, 260, 150), 1);

            let result = zinnia_recognizer_classify(rec, ch, 10);
            assert!(!result.is_null());

            let size = zinnia_result_size(result);
            assert!(size > 0);

            let mut values = Vec::new();

            for i in 0..size {
                let value_ptr = zinnia_result_value(result, i);
                assert!(!value_ptr.is_null());

                let value = CStr::from_ptr(value_ptr).to_string_lossy().into_owned();
                values.push(value);
            }

            assert!(
                values.iter().any(|v| v == "一"),
                "expected top-{size} results to contain 一, got: {values:?}"
            );
            assert_eq!(values[0], "一");
            zinnia_result_destroy(result);
            zinnia_character_destroy(ch);
            zinnia_recognizer_destroy(rec);
        }
    }
}
