use std::{
    ffi::{CStr, CString},
    path::Path,
    ptr::null_mut,
};

#[derive(Default, Debug)]
pub struct Recognizer {
    raw: *mut zinnia_sys::zinnia_recognizer_t,
}
#[derive(Default, Debug)]
pub struct Character {
    raw: *mut zinnia_sys::zinnia_character_t,
}

#[derive(Debug, Clone, PartialEq)]
pub struct Candidate {
    pub value: String,
    pub score: f32,
}
impl Character {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn set_width(&mut self, width: usize) -> Result<(), Error> {
        self.ensure_initialized()?;

        // SAFETY:
        // `ensure_initialized()` guarantees `self.raw` is a valid non-null character pointer.
        unsafe { zinnia_sys::zinnia_character_set_width(self.raw, width) };

        Ok(())
    }
    pub fn set_height(&mut self, height: usize) -> Result<(), Error> {
        self.ensure_initialized()?;

        // SAFETY:
        // `ensure_initialized()` guarantees `self.raw` is a valid non-null character pointer.
        unsafe { zinnia_sys::zinnia_character_set_height(self.raw, height) };

        Ok(())
    }
    pub fn add(&mut self, stroke_id: usize, x: i32, y: i32) -> Result<(), Error> {
        self.ensure_initialized()?;

        // SAFETY:
        // `ensure_initialized()` guarantees `self.raw` is a valid non-null character pointer.
        let ok = unsafe { zinnia_sys::zinnia_character_add(self.raw, stroke_id, x, y) };

        if ok == 0 {
            return Err(Error::Zinnia(self.error_message()));
        }

        Ok(())
    }
    pub fn clear(&mut self) -> Result<(), Error> {
        self.ensure_initialized()?;

        // SAFETY:
        // `ensure_initialized()` guarantees `self.raw` is a valid non-null character pointer.
        unsafe { zinnia_sys::zinnia_character_clear(self.raw) };

        Ok(())
    }
    fn error_message(&self) -> String {
        if self.raw.is_null() {
            return "character is not initialized".to_string();
        }

        // SAFETY:
        // `self.raw` is checked for null above. By type invariant, non-null means
        // it came from `zinnia_character_new` and has not yet been destroyed.
        let ptr = unsafe { zinnia_sys::zinnia_character_strerror(self.raw) };

        if ptr.is_null() {
            return "unknown zinnia error".to_string();
        }

        // SAFETY:
        // Zinnia returns a C string pointer for the error message when non-null.
        unsafe { CStr::from_ptr(ptr) }
            .to_string_lossy()
            .into_owned()
    }

    fn ensure_initialized(&mut self) -> Result<(), Error> {
        if self.raw.is_null() {
            // SAFETY:
            // Calls Zinnia's constructor function and stores the returned pointer.
            // A null return is handled as an error below.
            let res = unsafe { zinnia_sys::zinnia_character_new() };
            if res.is_null() {
                return Err(Error::InitializationFailed);
            }

            self.raw = res;
        }

        Ok(())
    }

    fn destroy_raw(&mut self) {
        if !self.raw.is_null() {
            // SAFETY:
            // `self.raw` is owned by this struct and was created by
            // `zinnia_character_new`. We only destroy it once here.
            unsafe { zinnia_sys::zinnia_character_destroy(self.raw) };
            self.raw = null_mut();
        }
    }
}

impl Recognizer {
    pub fn new() -> Self {
        Self::default()
    }
    pub fn open<P: AsRef<Path>>(&mut self, path: P) -> Result<(), Error> {
        self.destroy_raw();
        // SAFETY:
        // Calls Zinnia's constructor function and stores the returned pointer.
        // A null return is handled as an error below.
        let res = unsafe { zinnia_sys::zinnia_recognizer_new() };
        if res.is_null() {
            return Err(Error::InitializationFailed);
        }

        self.raw = res;

        let c_path = CString::new(path.as_ref().to_string_lossy().as_bytes())
            .map_err(|_| Error::PathContainsNul)?;

        // SAFETY:
        // -  `self.raw` is a valid non-null recognizer pointer.
        // - `c_path` is a valid NUL-terminated string.
        let ok = unsafe { zinnia_sys::zinnia_recognizer_open(self.raw, c_path.as_ptr()) };

        if ok == 0 {
            return Err(Error::Zinnia(self.error_message()));
        }

        Ok(())
    }
    pub fn classify(&self, character: &Character, nbest: usize) -> Result<Vec<Candidate>, Error> {
        if self.raw.is_null() {
            return Err(Error::Uninitialized);
        }

        if character.raw.is_null() {
            return Err(Error::Uninitialized);
        }

        // SAFETY:
        // - `self.raw` is checked for null above and is assumed valid.
        // - `character.raw` is checked for null above and is assumed valid.
        // - both pointers are owned by their wrappers and not freed for the duration of this call.
        let result =
            unsafe { zinnia_sys::zinnia_recognizer_classify(self.raw, character.raw, nbest) };

        if result.is_null() {
            return Err(Error::Zinnia(self.error_message()));
        }

        // SAFETY:
        // `result` is a valid non-null result pointer returned by Zinnia.
        let size = unsafe { zinnia_sys::zinnia_result_size(result) };

        let mut candidates = Vec::with_capacity(size);

        for i in 0..size {
            // SAFETY:
            // `result` is valid and `i < size`.
            let value_ptr = unsafe { zinnia_sys::zinnia_result_value(result, i) };
            if value_ptr.is_null() {
                continue;
            }

            let value = unsafe { CStr::from_ptr(value_ptr) }
                .to_string_lossy()
                .into_owned();

            // SAFETY:
            // `result` is valid and `i < size`.
            let score = unsafe { zinnia_sys::zinnia_result_score(result, i) };

            candidates.push(Candidate { value, score });
        }

        // SAFETY:
        // `result` was returned by `zinnia_recognizer_classify` and must be destroyed once.
        unsafe { zinnia_sys::zinnia_result_destroy(result) };

        Ok(candidates)
    }
    fn error_message(&self) -> String {
        if self.raw.is_null() {
            return "recognizer is not initialized".to_string();
        }

        // SAFETY:
        // `self.raw` is checked for null above. By type invariant, non-null means
        // it came from `zinnia_recognizer_new` and has not yet been destroyed.
        let ptr = unsafe { zinnia_sys::zinnia_recognizer_strerror(self.raw) };

        if ptr.is_null() {
            return "unknown zinnia error".to_string();
        }

        // SAFETY:
        // Zinnia returns a C string pointer for the error message when non-null.
        unsafe { CStr::from_ptr(ptr) }
            .to_string_lossy()
            .into_owned()
    }
    fn destroy_raw(&mut self) {
        if !self.raw.is_null() {
            // SAFETY:
            // `self.raw` is owned by this struct and was created by
            // `zinnia_recognizer_new`. We only destroy it once here.
            unsafe { zinnia_sys::zinnia_recognizer_destroy(self.raw) };
            self.raw = null_mut();
        }
    }
}

impl Drop for Recognizer {
    fn drop(&mut self) {
        self.destroy_raw();
    }
}

impl Drop for Character {
    fn drop(&mut self) {
        self.destroy_raw();
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Error {
    InitializationFailed,
    PathContainsNul,
    Zinnia(String),
    Uninitialized,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn recognizer_can_be_created() {
        let recognizer = Recognizer::new();
        assert!(recognizer.raw.is_null());
    }

    #[test]
    fn open_nonexistent_model_fails() {
        let mut recognizer = Recognizer::new();

        let err = recognizer.open("/definitely/not/found.model").unwrap_err();

        match err {
            Error::Zinnia(msg) => assert!(!msg.is_empty()),
            other => panic!("expected Error::Zinnia(_), got {other:?}"),
        }
    }

    #[test]
    fn open_valid_model_works() {
        let mut recognizer = Recognizer::new();

        let result = recognizer.open("../model/handwriting-ja.model");
        assert!(result.is_ok(), "open failed: {result:?}");
        assert!(!recognizer.raw.is_null());
    }

    #[test]
    fn reopening_valid_model_works() {
        let mut recognizer = Recognizer::new();

        recognizer.open("../model/handwriting-ja.model").unwrap();
        let first_ptr = recognizer.raw;

        recognizer.open("../model/handwriting-ja.model").unwrap();
        let second_ptr = recognizer.raw;

        assert!(!second_ptr.is_null());
        // not guaranteed to differ, so only check valid
        let _ = first_ptr;
    }
    #[test]
    fn character_can_be_created_lazily() {
        let ch = Character::new();
        assert!(ch.raw.is_null());
    }

    #[test]
    fn character_can_set_size_and_add_points() {
        let mut ch = Character::new();

        ch.set_width(300).unwrap();
        ch.set_height(300).unwrap();
        ch.add(0, 50, 150).unwrap();
        ch.add(0, 120, 150).unwrap();
        ch.add(0, 190, 150).unwrap();
        ch.add(0, 260, 150).unwrap();

        assert!(!ch.raw.is_null());
    }
    #[test]
    fn character_can_be_cleared() {
        let mut ch = Character::new();

        ch.set_width(300).unwrap();
        ch.set_height(300).unwrap();
        ch.add(0, 50, 150).unwrap();
        ch.clear().unwrap();

        assert!(!ch.raw.is_null());
    }
    #[test]
    fn classify_simple_stroke_returns_ichi() {
        let mut recognizer = Recognizer::new();
        recognizer.open("../model/handwriting-ja.model").unwrap();

        let mut ch = Character::new();
        ch.set_width(300).unwrap();
        ch.set_height(300).unwrap();
        ch.add(0, 50, 150).unwrap();
        ch.add(0, 120, 150).unwrap();
        ch.add(0, 190, 150).unwrap();
        ch.add(0, 260, 150).unwrap();

        let result = recognizer.classify(&ch, 10).unwrap();

        assert!(!result.is_empty());
        assert!(result.iter().any(|c| c.value == "一"), "got: {result:?}");
        assert_eq!(result[0].value, "一");
    }
    #[test]
    fn classify_simple_juu() {
        let mut recognizer = Recognizer::new();
        recognizer.open("../model/handwriting-ja.model").unwrap();

        let mut ch = Character::new();
        ch.set_width(300).unwrap();
        ch.set_height(300).unwrap();

        // horizontal
        ch.add(0, 90, 150).unwrap();
        ch.add(0, 130, 150).unwrap();
        ch.add(0, 170, 150).unwrap();
        ch.add(0, 210, 150).unwrap();

        // vertical
        ch.add(1, 150, 90).unwrap();
        ch.add(1, 150, 130).unwrap();
        ch.add(1, 150, 170).unwrap();
        ch.add(1, 150, 210).unwrap();

        let result = recognizer.classify(&ch, 10).unwrap();

        assert!(!result.is_empty());
        assert!(result.iter().any(|c| c.value == "十"), "got: {result:?}");
        assert_eq!(result[0].value, "十");
    }
}
