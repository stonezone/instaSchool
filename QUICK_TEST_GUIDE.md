# Student Mode - Quick Test Guide

## 🚀 5-Minute Test Plan

### Step 1: Start Application (30 seconds)
```bash
cd /Users/zackjordan/code/instaSchool
streamlit run main.py
```

### Step 2: Create Test Curriculum (2 minutes)
**If you already have curricula, skip to Step 3**

1. Mode: "👨‍🏫 Teacher (Create & Edit)"
2. Subject: "Math"
3. Grade: "5"
4. Number of units: "2" (for faster testing)
5. Click "Generate New Curriculum"
6. Wait for completion

### Step 3: Switch to Student Mode (10 seconds)
1. Sidebar → "🎒 Student (Learn & Practice)"
2. Verify teacher controls disappear
3. Verify student interface appears

### Step 4: Test Core Features (2 minutes)

**Navigation Test**:
- Click "✅ Complete & Continue" → Should see "+10 XP!"
- Click "⬅️ Previous" → Should go back one section
- Click "Skip ⏭️" → Should advance without XP

**Progress Test**:
- Note current XP (e.g., 20 XP)
- Refresh page (Cmd+R / Ctrl+R)
- Verify XP is same (progress saved!)

**Level-Up Test**:
- Complete 10 sections total (100 XP)
- Should see: "🎉 Level Up! You're now Level 1!"
- Balloons should appear

**Completion Test**:
- Complete all 12 sections (2 units × 6 sections)
- Should see: "🏆 Congratulations! Course Complete!"

---

## ✅ Success Checklist

Check each item:
- [ ] Mode selector visible in sidebar
- [ ] Student mode shows different interface
- [ ] Curriculum dropdown works
- [ ] Progress bar updates
- [ ] XP increases by 10 on complete
- [ ] Level-up happens at 100 XP
- [ ] Progress persists after refresh
- [ ] All section types display (intro, image, content, chart, quiz, summary)
- [ ] Navigation buttons work
- [ ] Course completion triggers

---

## 🐛 Quick Troubleshooting

**No curricula showing?**
→ Create one in Teacher Mode first

**Import error?**
→ Check `src/student_mode/__init__.py` exists

**Progress not saving?**
→ Check write permissions on `curricula/` folder

**XP not updating?**
→ Refresh page and check again

---

## 📊 What You Should See

### Sidebar (Student Mode):
```
🎓 InstaSchool
━━━━━━━━━━━━━━━━
○ Teacher (Create & Edit)
● Student (Learn & Practice)
━━━━━━━━━━━━━━━━

### 🎯 Your Progress
⭐ Level 0
🎯 20 XP (20/100 to Level 1)
[████░░░░░░] 20%
━━━━━━━━━━━━━━━━

📚 Choose Your Lesson
[Math - Grade 5 ▼]
```

### Main Area:
```
# 🎓 Math
Grade 5 • Interactive Style
━━━━━━━━━━━━━━━━━━━━━━━━━━

Progress: 16.7% [███░░░░░░░░░░░░░░░]

## 📖 Unit 1: Fractions
Section 2 of 6: Image
━━━━━━━━━━━━━━━━━━━━━━━━━━

### 🖼️ Visual Learning
[Image displayed here]
━━━━━━━━━━━━━━━━━━━━━━━━━━

[⬅️ Previous] [✅ Complete & Continue] [Skip ⏭️]
```

---

## 🎮 Full User Journey

1. Launch app
2. Select Student Mode
3. Choose curriculum
4. See Level 0, 0 XP
5. Complete section → +10 XP
6. See progress bar update
7. Continue through sections
8. Hit 100 XP → Level up! 🎉
9. Complete all sections → Course complete! 🏆
10. Click "Start Over" → Back to section 1

---

## 💾 Files Created During Testing

After testing, you'll find:
```
curricula/progress_curriculum_TIMESTAMP.json
```

This file contains student progress and can be deleted to reset progress.

---

**Test Time**: ~5 minutes  
**Expected Result**: All features working  
**Next**: Continue with Phase 2 or demo to stakeholders!
