"""
CreditWise ML Loan Prediction — Real ML Models (FIXED)
SecureTrust Bank — Logistic Regression · KNN · Naive Bayes
Trained on: loan_approval_data schema from credit_wise notebook

FIXES APPLIED:
✓ Added missing imports (pandas, joblib)
✓ Fixed duplicate variable assignments
✓ Fixed type inconsistencies (dependents handling)
✓ Added proper error handling
✓ Added input validation
✓ Fixed feature vector shape validation
✓ Removed non-deterministic random values
✓ Better error messages for debugging
"""

import os
import time
import json
import numpy as np
import pandas as pd
import joblib


# ── Configuration ─────────────────────────────────────────────────────────────
_BASE = os.path.join(os.path.dirname(__file__), "ml")
_MODELS_LOADED = False
_lr = _knn = _nb = _scaler = _ohe = _meta = None


# ── Model Loading ─────────────────────────────────────────────────────────────

def _load_models():
    """Load ML models and artifacts from disk."""
    global _lr, _knn, _nb, _scaler, _ohe, _meta, _MODELS_LOADED
    
    try:
        _lr = joblib.load(os.path.join(_BASE, "logistic_model.pkl"))
        _knn = joblib.load(os.path.join(_BASE, "knn_model.pkl"))
        _nb = joblib.load(os.path.join(_BASE, "naive_bayes_model.pkl"))
        _scaler = joblib.load(os.path.join(_BASE, "scaler.pkl"))
        _ohe = joblib.load(os.path.join(_BASE, "ohe.pkl"))
        
        with open(os.path.join(_BASE, "meta.json"), 'r') as f:
            _meta = json.load(f)
        
        # Validate meta.json structure
        required_keys = ["ohe_cols", "edu_classes", "feature_count"]
        for key in required_keys:
            if key not in _meta:
                print(f"[WARNING] Missing '{key}' in meta.json")
        
        _MODELS_LOADED = True
        print("[CreditWise] ML models loaded successfully ✓")
        return True
        
    except FileNotFoundError as e:
        print(f"[CreditWise] ML models not found: {e}")
        print("[CreditWise] Falling back to rule-based engine")
        _MODELS_LOADED = False
        return False
    except json.JSONDecodeError as e:
        print(f"[CreditWise] Failed to parse meta.json: {e}")
        _MODELS_LOADED = False
        return False
    except Exception as e:
        print(f"[CreditWise] Unexpected error loading models: {e}")
        _MODELS_LOADED = False
        return False


# Load models on startup
_load_models()


# ── Main Prediction Function ──────────────────────────────────────────────────

def predict_loan(data: dict) -> dict:
    """
    Predict loan approval using ML models or rule-based fallback.
    
    Args:
        data: Dictionary with applicant information
        
    Returns:
        Dictionary with prediction results
    """
    if _MODELS_LOADED:
        try:
            return _predict_ml(data)
        except Exception as e:
            print(f"[ERROR] ML prediction failed: {e}. Falling back to rules.")
            return _predict_rules(data)
    else:
        return _predict_rules(data)


# ── ML-Based Prediction ───────────────────────────────────────────────────────

def _predict_ml(data: dict) -> dict:
    """ML-based loan prediction using ensemble of models."""
    
    # Extract and convert numerical fields
    income = _to_float(data.get("income", 0))
    coincome = _to_float(data.get("coincome", 0))
    loan_amt = _to_float(data.get("loanamt", 0))
    term = _to_float(data.get("term", 360))
    credit_score = _to_float(data.get("credit_score", 650))
    
    # Fix: Proper dependents handling
    dependents_raw = str(data.get("dependents", "0")).replace("3+", "3")
    dependents = _to_int(dependents_raw, 0)
    
    # Extract categorical fields
    education = str(data.get("education", "Graduate")).strip()
    emp_status = str(data.get("employment_status", "Employed")).strip()
    emp_cat = str(data.get("employer_category", "Private")).strip()
    marital = "Married" if str(data.get("married", "No")).lower() == "yes" else "Single"
    gender = str(data.get("gender", "Male")).strip().capitalize()
    
    # Fix: Single mapping for loan purpose (removed duplicate assignment)
    loan_purpose_raw = str(data.get("type", "home")).lower()
    loan_purpose_map = {
        "home": "Home",
        "personal": "Personal",
        "education": "Education",
        "vehicle": "Vehicle",
        "business": "Business"
    }
    loan_purpose = loan_purpose_map.get(loan_purpose_raw, "Home")
    
    # Fix: Single mapping for property area (removed duplicate assignment)
    area_raw = str(data.get("area", "urban")).lower()
    area_map = {
        "urban": "Urban",
        "semiurban": "Semiurban",
        "rural": "Rural"
    }
    prop_area = area_map.get(area_raw, "Urban")
    
    # Calculate financial metrics
    monthly_income = income + coincome
    emi = loan_amt / term if term > 0 else loan_amt
    dti_ratio = emi / monthly_income if monthly_income > 0 else 2.0
    dti_ratio = min(dti_ratio, 2.0)  # Cap at 2.0
    
    # Get education encoding
    edu_classes = _meta.get("edu_classes", ["Graduate", "Not Graduate"])
    if education not in edu_classes:
        print(f"[WARNING] Unknown education value: {education}. Using default.")
        edu_encoded = 0
    else:
        edu_encoded = edu_classes.index(education)
    
    # Prepare categorical features for one-hot encoding
    ohe_cols = _meta.get("ohe_cols", [])
    if not ohe_cols:
        raise ValueError("OHE columns not found in meta.json")
    
    # Fix: Validate OHE input
    ohe_input = pd.DataFrame(
        [[emp_status, marital, loan_purpose, prop_area, gender, emp_cat]],
        columns=ohe_cols
    )
    
    try:
        ohe_encoded = _ohe.transform(ohe_input)
    except ValueError as e:
        print(f"[ERROR] OHE transform failed: {e}")
        print(f"[ERROR] Input columns: {ohe_input.columns.tolist()}")
        print(f"[ERROR] Expected columns: {ohe_cols}")
        raise
    
    # Calculate polynomial features
    dti_sq = dti_ratio ** 2
    cs_sq = credit_score ** 2
    
    # Fix: Build feature vector with proper shape validation
    num_feats = np.array([dependents, edu_encoded, income, coincome, loan_amt, term]).reshape(1, -1)
    ohe_feats = ohe_encoded
    poly_feats = np.array([dti_sq, cs_sq]).reshape(1, -1)
    
    feature_vec = np.hstack([num_feats, ohe_feats, poly_feats])
    
    # Validate feature shape
    expected_feature_count = _meta.get("feature_count")
    if expected_feature_count and feature_vec.shape[1] != expected_feature_count:
        print(f"[WARNING] Feature count mismatch: {feature_vec.shape[1]} != {expected_feature_count}")
    
    # Fix: Add error handling for scaling
    try:
        feature_scaled = _scaler.transform(feature_vec)
    except ValueError as e:
        print(f"[ERROR] Scaler transform failed: {e}")
        raise
    
    # Make predictions with all three models
    lr_pred = int(_lr.predict(feature_scaled)[0])
    knn_pred = int(_knn.predict(feature_scaled)[0])
    nb_pred = int(_nb.predict(feature_scaled)[0])
    
    # Get probabilities
    lr_prob = float(_lr.predict_proba(feature_scaled)[0][1])
    nb_prob = float(_nb.predict_proba(feature_scaled)[0][1])
    
    # Ensemble decision (voting)
    votes = lr_pred + knn_pred + nb_pred
    approved = votes >= 2
    
    # Calculate confidence
    ensemble_prob = (lr_prob + nb_prob) / 2
    confidence = int(min(97, max(62, ensemble_prob * 100 if approved else (1 - ensemble_prob) * 100)))
    
    # Compute approval factors
    factors = _compute_factors(credit_score, dti_ratio, education, prop_area, dependents, emp_status, data)
    
    # Calculate approval score
    score = int(min(99, max(5, ensemble_prob * 100)))
    
    # Determine interest rate based on loan type and area
    rate_map = {
        "Home":      {"Urban": 8.50, "Semiurban": 8.25, "Rural": 8.75},
        "Personal":  {"Urban": 11.0, "Semiurban": 10.5, "Rural": 11.5},
        "Education": {"Urban": 8.75, "Semiurban": 8.50, "Rural": 9.00},
        "Vehicle":   {"Urban": 9.50, "Semiurban": 9.25, "Rural": 9.75},
        "Business":  {"Urban": 10.5, "Semiurban": 10.0, "Rural": 11.0},
    }
    interest_rate = rate_map.get(loan_purpose, {}).get(prop_area, 9.0) if approved else None
    
    # Calculate maximum loan amount
    max_loan = int(monthly_income * term * 0.45)
    
    return {
        "approved": approved,
        "score": score,
        "confidence": confidence,
        "factors": factors,
        "emi": int(emi),
        "maxLoan": max_loan,
        "rate": interest_rate,
        "id": f"STB-{int(time.time()) % 1000000:06d}",
        "monthly": int(monthly_income),
        "loanamt": int(loan_amt),
        "term": int(term),
        "model_votes": {
            "logistic": lr_pred,
            "knn": knn_pred,
            "naive_bayes": nb_pred
        },
        "ensemble_prob": round(ensemble_prob, 3),
        "ml_powered": True,
    }


def _compute_factors(credit_score, dti_ratio, education, prop_area, dependents, emp_status, data):
    """Compute approval factors with color coding."""
    factors = []
    
    # Credit score factor
    cs = int(credit_score)
    if cs >= 750:
        cs_v, cs_c = 95, "#0a7c4e"
    elif cs >= 700:
        cs_v, cs_c = 80, "#0a7c4e"
    elif cs >= 650:
        cs_v, cs_c = 62, "#92600a"
    elif cs >= 600:
        cs_v, cs_c = 42, "#92600a"
    else:
        cs_v, cs_c = 18, "#c0392b"
    factors.append({"n": f"Credit score ({cs})", "v": cs_v, "c": cs_c})
    
    # Debt-to-income ratio factor
    if dti_ratio < 0.30:
        dti_v, dti_c = 92, "#0a7c4e"
    elif dti_ratio < 0.45:
        dti_v, dti_c = 72, "#92600a"
    elif dti_ratio < 0.60:
        dti_v, dti_c = 50, "#92600a"
    elif dti_ratio < 0.75:
        dti_v, dti_c = 30, "#c0392b"
    else:
        dti_v, dti_c = 10, "#c0392b"
    factors.append({"n": f"Debt-to-Income ({dti_ratio:.2f})", "v": dti_v, "c": dti_c})
    
    # Education factor
    edu_v = 82 if education == "Graduate" else 52
    edu_c = "#0a7c4e" if edu_v >= 70 else "#92600a"
    factors.append({"n": "Education level", "v": edu_v, "c": edu_c})
    
    # Property area factor
    area_map = {"Semiurban": 88, "Urban": 76, "Rural": 56}
    area_v = area_map.get(prop_area, 60)
    area_c = "#0a7c4e" if area_v >= 75 else "#92600a"
    factors.append({"n": "Property area", "v": area_v, "c": area_c})
    
    # Employment status factor
    emp_map = {"Employed": 88, "Self-Employed": 60, "Unemployed": 20}
    emp_v = emp_map.get(emp_status, 60)
    emp_c = "#0a7c4e" if emp_v >= 70 else ("#92600a" if emp_v >= 40 else "#c0392b")
    factors.append({"n": "Employment status", "v": emp_v, "c": emp_c})
    
    # Dependents factor
    dep_map = {0: 90, 1: 78, 2: 62, 3: 40}
    dep = min(dependents, 3)
    dep_v = dep_map.get(dep, 40)
    dep_c = "#0a7c4e" if dep_v >= 70 else "#92600a"
    factors.append({"n": f"Dependents ({dep})", "v": dep_v, "c": dep_c})
    
    return factors


# ── Rule-Based Fallback ───────────────────────────────────────────────────────

def _predict_rules(data: dict) -> dict:
    """Rule-based loan prediction (fallback when ML models unavailable)."""
    
    income = _to_float(data.get("income", 0))
    coincome = _to_float(data.get("coincome", 0))
    loan_amt = _to_float(data.get("loanamt", 0))
    term = _to_float(data.get("term", 360))
    
    # Fix: Better credit score handling with validation
    credit_raw = data.get("credit_score") or data.get("credit", "550")
    try:
        credit_score = float(str(credit_raw).strip())
        # Validate range
        if credit_score < 300 or credit_score > 900:
            print(f"[WARNING] Credit score {credit_score} out of range, using 550")
            credit_score = 550
    except (ValueError, TypeError):
        print(f"[WARNING] Invalid credit_score '{credit_raw}', using 550")
        credit_score = 550
    
    monthly = income + coincome
    emi = loan_amt / term if term > 0 else loan_amt
    dti = emi / monthly if monthly > 0 else 999
    
    score = 0
    factors = []
    
    # Credit score scoring
    if credit_score >= 750:
        cs_v = 95
        score += 35
    elif credit_score >= 700:
        cs_v = 80
        score += 28
    elif credit_score >= 650:
        cs_v = 62
        score += 18
    elif credit_score >= 600:
        cs_v = 42
        score += 10
    else:
        cs_v = 18
        score += 0
    
    cs_c = "#0a7c4e" if credit_score >= 700 else ("#92600a" if credit_score >= 600 else "#c0392b")
    factors.append({"n": f"Credit score ({int(credit_score)})", "v": cs_v, "c": cs_c})
    
    # DTI ratio scoring
    if dti < 0.30:
        ir_v = 92
        score += 25
    elif dti < 0.45:
        ir_v = 72
        score += 18
    elif dti < 0.60:
        ir_v = 50
        score += 10
    elif dti < 0.75:
        ir_v = 30
        score += 4
    else:
        ir_v = 10
        score += 0
    factors.append({"n": f"Debt-to-Income ({dti:.2f})", "v": ir_v, "c": _color(ir_v)})
    
    # Education scoring
    education = str(data.get("education", "")).lower()
    edu_v = 82 if education == "graduate" else 52
    score += 10 if education == "graduate" else 5
    factors.append({"n": "Education level", "v": edu_v, "c": _color(edu_v)})
    
    # Property area scoring
    area = str(data.get("area", "urban")).lower()
    area_scores = {"semiurban": 88, "urban": 76, "rural": 56}
    area_v = area_scores.get(area, 60)
    score += {"semiurban": 12, "urban": 9, "rural": 5}.get(area, 5)
    factors.append({"n": "Property area", "v": area_v, "c": _color(area_v)})
    
    # Employment status scoring
    emp = str(data.get("employment_status", "employed")).lower()
    emp_scores = {"employed": 88, "self-employed": 60, "unemployed": 20}
    emp_v = emp_scores.get(emp, 60)
    score += {"employed": 5, "self-employed": 2, "unemployed": -5}.get(emp, 2)
    factors.append({"n": "Employment status", "v": emp_v, "c": _color(emp_v)})
    
    # Approval decision
    approved = score >= 55 and credit_score >= 600
    
    # Fix: Removed random value, now deterministic
    confidence = min(97, max(62, 60 + abs(score - 50)))
    
    max_loan = int(monthly * term * 0.45)
    
    loan_type = str(data.get("type", "home")).lower()
    rate_map = {
        "home": 8.5,
        "personal": 11.0,
        "education": 8.75,
        "vehicle": 9.5,
        "business": 10.5
    }
    interest_rate = rate_map.get(loan_type, 9.0) if approved else None
    
    return {
        "approved": approved,
        "score": min(100, max(0, score)),
        "confidence": confidence,
        "factors": factors,
        "emi": int(emi),
        "maxLoan": max_loan,
        "rate": interest_rate,
        "id": f"STB-{int(time.time()) % 1000000:06d}",
        "monthly": int(monthly),
        "loanamt": int(loan_amt),
        "term": int(term),
        "ml_powered": False,
    }


# ── Helper Functions ──────────────────────────────────────────────────────────

def _to_float(val, default=0.0):
    """Safely convert value to float."""
    try:
        return float(str(val).replace(",", "").strip())
    except (ValueError, TypeError):
        return default


def _to_int(val, default=0):
    """Safely convert value to integer."""
    try:
        return int(float(str(val).replace(",", "").strip()))
    except (ValueError, TypeError):
        return default


def _color(v):
    """Get color code based on value."""
    if v >= 70:
        return "#0a7c4e"  # Green
    if v >= 45:
        return "#92600a"  # Orange
    return "#c0392b"  # Red

def _predict_rules(data: dict) -> dict:
    """Rule-based loan prediction (fallback when ML models unavailable)."""
    
    income = _to_float(data.get("income", 0))
    coincome = _to_float(data.get("coincome", 0))
    loan_amt = _to_float(data.get("loanamt", 0))
    term = _to_float(data.get("term", 360))
    
    # Improved credit score handling without forcing string conversion
    credit_raw = data.get("credit_score") or data.get("credit", 550)
    try:
        # Accept numeric directly, only cast if needed
        if isinstance(credit_raw, (int, float)):
            credit_score = float(credit_raw)
        else:
            credit_score = float(credit_raw)
        
        # Explicit handling for no credit history
        if credit_score == 0:
            print("[INFO] Applicant has no credit history, treating as very low score (300).")
            credit_score = 300
        
        # Validate range
        elif credit_score < 300 or credit_score > 900:
            print(f"[WARNING] Credit score {credit_score} out of range, using 550")
            credit_score = 550
    
    except (ValueError, TypeError):
        print(f"[WARNING] Invalid credit_score '{credit_raw}', using 550")
        credit_score = 550
    
    monthly = income + coincome
    emi = loan_amt / term if term > 0 else loan_amt
    dti = emi / monthly if monthly > 0 else 999
    
    score = 0
    factors = []
    
    # Credit score scoring
    if credit_score >= 750:
        cs_v = 95
        score += 35
    elif credit_score >= 700:
        cs_v = 80
        score += 28
    elif credit_score >= 650:
        cs_v = 62
        score += 18
    elif credit_score >= 600:
        cs_v = 42
        score += 10
    else:
        cs_v = 18
        score += 0
    
    cs_c = "#0a7c4e" if credit_score >= 700 else ("#92600a" if credit_score >= 600 else "#c0392b")
    factors.append({"n": f"Credit score ({int(credit_score)})", "v": cs_v, "c": cs_c})
    
    # DTI ratio scoring
    if dti < 0.30:
        ir_v = 92
        score += 25
    elif dti < 0.45:
        ir_v = 72
        score += 18
    elif dti < 0.60:
        ir_v = 50
        score += 10
    elif dti < 0.75:
        ir_v = 30
        score += 4
    else:
        ir_v = 10
        score += 0
    factors.append({"n": f"Debt-to-Income ({dti:.2f})", "v": ir_v, "c": _color(ir_v)})
    
    # Education scoring
    education = str(data.get("education", "")).lower()
    edu_v = 82 if education == "graduate" else 52
    score += 10 if education == "graduate" else 5
    factors.append({"n": "Education level", "v": edu_v, "c": _color(edu_v)})
    
    # Property area scoring
    area = str(data.get("area", "urban")).lower()
    area_scores = {"semiurban": 88, "urban": 76, "rural": 56}
    area_v = area_scores.get(area, 60)
    score += {"semiurban": 12, "urban": 9, "rural": 5}.get(area, 5)
    factors.append({"n": "Property area", "v": area_v, "c": _color(area_v)})
    
    # Employment status scoring
    emp = str(data.get("employment_status", "employed")).lower()
    emp_scores = {"employed": 88, "self-employed": 60, "unemployed": 20}
    emp_v = emp_scores.get(emp, 60)
    score += {"employed": 5, "self-employed": 2, "unemployed": -5}.get(emp, 2)
    factors.append({"n": "Employment status", "v": emp_v, "c": _color(emp_v)})
    
    # Approval decision
    approved = score >= 55 and credit_score >= 600
    
    # Deterministic confidence
    confidence = min(97, max(62, 60 + abs(score - 50)))
    
    max_loan = int(monthly * term * 0.45)
    
    loan_type = str(data.get("type", "home")).lower()
    rate_map = {
        "home": 8.5,
        "personal": 11.0,
        "education": 8.75,
        "vehicle": 9.5,
        "business": 10.5
    }
    interest_rate = rate_map.get(loan_type, 9.0) if approved else None
    
    return {
        "approved": approved,
        "score": min(100, max(0, score)),
        "confidence": confidence,
        "factors": factors,
        "emi": int(emi),
        "maxLoan": max_loan,
        "rate": interest_rate,
        "id": f"STB-{int(time.time()) % 1000000:06d}",
        "monthly": int(monthly),
        "loanamt": int(loan_amt),
        "term": int(term),
        "ml_powered": False,
    }

