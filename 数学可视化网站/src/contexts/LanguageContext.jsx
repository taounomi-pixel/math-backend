import React, { createContext, useContext, useState, useEffect } from 'react';

const translations = {
  en: {
    // Header
    searchPlaceholder: "Search theorems, topics, or creators...",
    langEN: "English (EN)",
    langZH: "简体中文 (ZH)",
    langFR: "Français (FR)",
    upload: "Upload",
    signIn: "Sign In",
    logout: "Logout",
    
    // Auth Modal
    loginTitle: "Sign In",
    registerTitle: "Create Account",
    username: "Username",
    password: "Password",
    continueBtn: "Continue",
    createAccountBtn: "Create Account",
    noAccount: "Don't have an account? ",
    hasAccount: "Already have an account? ",
    signUpLink: "Sign up",
    signInLink: "Sign in",
    
    loginFail: "Login failed",
    regFail: "Registration failed",
    regSuccess: "Registration successful! Please sign in.",
    
    // Sidebar & Topics
    "All Topics": "All Topics",
    "Calculus": "Calculus",
    "Geometry": "Geometry",
    "Linear Algebra": "Linear Algebra",
    "Number Theory": "Number Theory",
    "Topology": "Topology",
    "Probability": "Probability",
    
    // Home Page Descriptions
    descWait: "The main video grid will be rendered here.",
    descCalculus: "Calculus is the mathematical study of continuous change... 积分与微积分的动画展示。",
    descGeometry: "Exploring shapes, sizes, relative positions, and properties of space... 几何学的魅力。",
    descLinear: "Vectors, vector spaces, linear transformations, and matrices... 线性代数的本质。",
    descNumber: "The study of integers and integer-valued functions... 数论探秘。",
    descTopology: "Properties that are preserved through deformations, twistings, and stretchings... 拓扑结构可视。",
    descProbability: "The mathematics of measuring the likelihood of events... 概率与统计。",
    descNotFound: "The page you are looking for does not exist.",
    titleNotFound: "404 - Not Found",
    
    // TheoremCard
    loading: "Loading...",
    loginToLike: "Please log in to like videos!",
    noRecords: "No visualizations found",
    loginToUploadDesc: "Log in and click Upload to share your first mathematical animation!",
    noResultsFor: "No results found for",
    uploadedBy: "Uploaded by",
    uploadedOn: "Uploaded on",
    likes: "Likes",
    
    // UploadModal
    uploadVideo: "Upload Visualization",
    title: "Title",
    titlePlaceholder: "e.g. Fourier Transform Explained",
    videoFile: "MP4 Video File",
    selectFileHint: "Click to select a local MP4 file",
    btnUploading: "Uploading...",
    btnUpload: "Upload Video",
    errInvalidFile: "Please select a valid .mp4 file.",
    errFieldsRequired: "Both title and MP4 file are required.",
    errLoginRequired: "You must be logged in to upload.",
    errUploadFail: "Upload failed",
    
    // Delete
    btnDelete: "Delete",
    deleteConfirm: "Are you sure you want to delete this video? This action cannot be undone.",
    errDeleteFail: "Failed to delete video.",
    deleteSuccess: "Video deleted successfully.",
    
    // Manim Source
    manimSource: "Manim Source Code (Optional)",
    sourceFileHint: "Select .py file",
    viewCode: "View Code",
    errInvalidSource: "Please select a valid .py file for Manim source."
  },
  zh: {
    // Header
    searchPlaceholder: "搜索定理、主题或创作者...",
    langEN: "English (EN)",
    langZH: "简体中文 (ZH)",
    langFR: "Français (FR)",
    upload: "上传",
    signIn: "登入",
    logout: "注销",
    
    // Auth Modal
    loginTitle: "登入",
    registerTitle: "创建账户",
    username: "用户名",
    password: "密码",
    continueBtn: "继续",
    createAccountBtn: "创建账户",
    noAccount: "还没有账号？ ",
    hasAccount: "已经有账号了？ ",
    signUpLink: "注册",
    signInLink: "登入",
    
    loginFail: "登入失败",
    regFail: "注册失败",
    regSuccess: "注册成功！请登入。",
    
    // Sidebar & Topics
    "All Topics": "所有主题",
    "Calculus": "微积分",
    "Geometry": "几何学",
    "Linear Algebra": "线性代数",
    "Number Theory": "数论",
    "Topology": "拓扑学",
    "Probability": "概率统计",
    
    // Home Page Descriptions
    descWait: "主要的视频网格将渲染在此处。",
    descCalculus: "微积分是研究连续变化的数学分支... 积分与导数的动画展示。",
    descGeometry: "探索形状、大小、相对位置和空间性质... 几何学的魅力。",
    descLinear: "向量、向量空间、线性变换和矩阵... 线性代数的本质。",
    descNumber: "研究整数和整数值函数的学问... 数论探秘。",
    descTopology: "研究空间在连续变形下保持不变的性质... 拓扑结构可视。",
    descProbability: "衡量事件发生可能性的数学... 概率与统计。",
    descNotFound: "您寻找的页面不存在。",
    titleNotFound: "404 - 找不到页面",
    
    // TheoremCard
    loading: "加载中...",
    loginToLike: "请登录以点赞视频！",
    noRecords: "暂无可用的可视化内容",
    loginToUploadDesc: "请登录并点击上传来分享你的第一个数学动画！",
    noResultsFor: "未找到符合的结果：",
    uploadedBy: "上传者 ",
    uploadedOn: "上传于 ",
    likes: "喜欢",
    
    // UploadModal
    uploadVideo: "上传可视化项目",
    title: "标题",
    titlePlaceholder: "例如：傅里叶变换的直观解释",
    videoFile: "MP4 视频文件",
    selectFileHint: "点击选择本地的 MP4 视频文件",
    btnUploading: "上传中...",
    btnUpload: "上传视频",
    errInvalidFile: "请选择一个有效的 .mp4 格式文件。",
    errFieldsRequired: "标题和视频文件均为必填项。",
    errLoginRequired: "你需要登录后才能上传视频。",
    errUploadFail: "上传失败",
    
    // 删除
    btnDelete: "删除",
    deleteConfirm: "你确定要删除这段视频吗？此操作无法撤销。",
    errDeleteFail: "删除视频失败。",
    deleteSuccess: "视频已成功删除。",
    
    // Manim 源码
    manimSource: "Manim 源代码 (可选)",
    sourceFileHint: "选择 .py 文件",
    viewCode: "查看代码",
    errInvalidSource: "请选择一个有效的 .py 格式文件作为源码。"
  }
};

const LanguageContext = createContext();

export const LanguageProvider = ({ children }) => {
  const [lang, setLang] = useState(() => {
    return localStorage.getItem('site_lang') || 'zh';
  });

  useEffect(() => {
    localStorage.setItem('site_lang', lang);
  }, [lang]);

  const t = (key) => {
    if (!translations[lang]) return key;
    return translations[lang][key] || key;
  };

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => useContext(LanguageContext);
