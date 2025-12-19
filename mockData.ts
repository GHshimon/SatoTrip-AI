import { Plan, Spot, Hotel, AdminStat, User } from './types';

export const currentUser = {
  id: 'u1',
  name: 'Sato User',
  avatar: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCQimBnBOGaV17gHnC1PXEG8Jb6btHzlwS_BeDfQq09PkPFjrYpGK4Ke0rjcyh2P1ov-dRtcmD_3fCir1TtililZWticg3jwg1Mp_RNZTRyBDDs6A0r_3z0mmQVXvxrvCESPAFGNK-dJF1L9eBM_cMJtGkZiOKxnd33GCuBnFraxGDyBaEAM7_eIpcyu7cIpynh6bwofwvO74oG5d3MKre2oFe6VxavIIMnS04h0amfRdsxI0CDLg4W9D6T6IVA61AWpctpgINplfQ',
  role: 'admin' as const
};

// Mock Users List for Admin
export const users: User[] = [
  currentUser,
  {
    id: 'u2',
    name: '田中 太郎',
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Taro',
    role: 'user'
  },
  {
    id: 'u3',
    name: '鈴木 花子',
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Hanako',
    role: 'user'
  },
  {
    id: 'u4',
    name: 'John Smith',
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=John',
    role: 'user'
  },
  {
    id: 'u5',
    name: 'Emily Davis',
    avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Emily',
    role: 'user'
  }
];

export const spots: Spot[] = [
  {
    id: 's1',
    name: '金閣寺（鹿苑寺）',
    description: '鏡湖池に映る金色の舎利殿が圧巻の美しさ。',
    area: 'Kyoto',
    category: 'History',
    durationMinutes: 60,
    rating: 4.8,
    image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAShXYjdbz-HnK7UqIW4uc4AZ496i8tXykch0UKvnQwe6n_9a-cv___S2BV1YSadUeJVTnb6Ac-Xn9i8P895lfgnXKB2U_Ql8IrJtWNuPO5bTkYvlbHbTxaqI8zSTD6EDZgX0v1YPMM6z12OloKCQ9oTnD5cf5viHlpjgpDJZow2SEA22XtgaZFIgDrllAmfp-2dXo7BO3x0_r-wEZPTXsKb_Yu3XbV-TCPEc-e9_CB0HrJbOsJ_4A7dzX6ycs0hafPVW8HFBVX_Wc',
    location: { lat: 35.0394, lng: 135.7292 }
  },
  {
    id: 's2',
    name: '伏見稲荷大社',
    description: '朱色の「千本鳥居」が続く幻想的な参道。',
    area: 'Kyoto',
    category: 'History',
    durationMinutes: 90,
    rating: 4.9,
    image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAIE9KY3NbwOR_uiyFxDVZghfvQkwD-MLEiMsYd3OWTd2PZVlugkL73UpjtfuR27PT9dGvsp6yba1AIFSkGvW9u9cVyWC8bNTlZY61SJIv92jn8jRNntaXLuEuyLDlKkMFLSpAAHq0aeUF-QQZE6KdIOnRYPTS4izKkioibuNR3vT83IorS0ejLIGlzO3Vuy2f4auwI2HounBs0OyWvPFsXbCpuE1aaGS6xTTFvICOVyv-2OJJc7dt4PaywbEmrpz9fhKDYDgM02wM',
    location: { lat: 34.9671, lng: 135.7727 }
  },
  {
    id: 's3',
    name: '嵐山 竹林の小径',
    description: '高く伸びる竹に囲まれた、静かで美しい散策路。',
    area: 'Kyoto',
    category: 'Nature',
    durationMinutes: 45,
    rating: 4.7,
    image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAeVnterwZUcIr_dHrmXTHWem-fhJZYrRIWmGMZwaJ5KBTdMdVCQMT6KKrR8xh6-l0UMa0T2adzosld8R0KhwIM-r1FcuFvrEqutfFparfHDvBKIMg51csqjQKS1vsXZwDbGrOyTQF2jjBtvUyAP3uCnTHRSNoDlBgQzR3rYtQmRKFkjlP_haiSWh8e27yLW5bualqrI1L_rL2cgDS_brxRCN2nhQDimZbzFS9uykDAREpHbJpzQfrwr3ccva-Suc4VexVJ1kbMN5g',
    location: { lat: 35.0169, lng: 135.6713 }
  },
  {
    id: 's4',
    name: '三鷹の森ジブリ美術館',
    description: 'ジブリの世界観に浸れる美術館。',
    area: 'Tokyo',
    category: 'Art',
    durationMinutes: 120,
    rating: 4.9,
    image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuArmdAAUBEs4_kBwVdTmpuR2OfwVfsnuqpfOW8o6YWTUrdw0JI4zs3pJeMtgQpXsDVnHvoaRj71X4LCZjWiSWhNozFKug1GWGnWbuGJjbUpFz5cOnU05JAyR-ZPjvc3AFBjpphbBBQJP7OysashtY3lbHqk094CidIAJKIGNzTHdRA7CYfNkRDzFrbowwxcaAizYWLVJyznEgBOEQBUehT5glYdGF_rLl-QC2lRGHfMCIUGg6mg_xMYsBvBYOvctwU3eC0toiGleIk',
    location: { lat: 35.6963, lng: 139.5704 }
  },
  {
    id: 's5',
    name: '新宿御苑',
    description: '都会のオアシス。四季折々の自然が楽しめる。',
    area: 'Tokyo',
    category: 'Nature',
    durationMinutes: 120,
    rating: 4.6,
    image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBiz9O1N-rC38EKaCKrZkWnHlT3BNZ2_ioD-wgiVPdzSpMhKhO3bsYTdlN2d962ouh2Y6ndN2m2hwwi66cHtF8va1NmQDzbPm6gsD_f3ENFYpul8C5xCQdYyg5L4F2oehZ-RSaX3qsSkHVRo8VZHV29PQLIzodnZHTMLmXCXafeYw58rsj-upDlQ8YS0PO5cSMWGxG5cdIDktT9M9QWLREsNF9yEIr9OtF4iA9jik2eiDxlCKhBXzXvcWZ8ezofvaAEYUy0SSh-dLs',
    location: { lat: 35.6852, lng: 139.7101 }
  },
  {
    id: 's6',
    name: '渋谷スクランブル交差点',
    description: '世界で最も混雑する交差点の一つ。',
    area: 'Tokyo',
    category: 'Culture',
    durationMinutes: 30,
    rating: 4.5,
    image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCdz-G_h0k6RJ3ry5mYzbSplIUw_uZ5qvm3fcvKuTI_XYyFKcG68gUEetqtlQsV6_U1xlG079Vpq_TmxVlDP2d2K96Sfhx1rjR-3m6bWu5Ku1CyVc2kxCAgomaqoyXdIumn0GcRGUIXu9M03dG1mDlpgkUnoSxGNOuJkRg14Zn1UxD0jfMbySj3L6sxEdOnU_UuEM0WYzUQm4ddP4z7fnsvSYyZ8lfcSe42HtmUn6qJPpDhy-vShozL-8t_hPBHxrFvo2btn6-mH-U',
    location: { lat: 35.6595, lng: 139.7004 }
  },
  {
    id: 's7',
    name: '桜島',
    description: '鹿児島のシンボルである活火山。迫力ある噴煙と溶岩原の景観。',
    area: 'Kagoshima',
    category: 'Nature',
    durationMinutes: 180,
    rating: 4.7,
    image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAeVnterwZUcIr_dHrmXTHWem-fhJZYrRIWmGMZwaJ5KBTdMdVCQMT6KKrR8xh6-l0UMa0T2adzosld8R0KhwIM-r1FcuFvrEqutfFparfHDvBKIMg51csqjQKS1vsXZwDbGrOyTQF2jjBtvUyAP3uCnTHRSNoDlBgQzR3rYtQmRKFkjlP_haiSWh8e27yLW5bualqrI1L_rL2cgDS_brxRCN2nhQDimZbzFS9uykDAREpHbJpzQfrwr3ccva-Suc4VexVJ1kbMN5g',
    location: { lat: 31.5833, lng: 130.6500 }
  },
  {
    id: 's8',
    name: '仙巌園',
    description: '桜島を築山に、錦江湾を池に見立てた雄大な大名庭園。',
    area: 'Kagoshima',
    category: 'History',
    durationMinutes: 90,
    rating: 4.6,
    image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBiz9O1N-rC38EKaCKrZkWnHlT3BNZ2_ioD-wgiVPdzSpMhKhO3bsYTdlN2d962ouh2Y6ndN2m2hwwi66cHtF8va1NmQDzbPm6gsD_f3ENFYpul8C5xCQdYyg5L4F2oehZ-RSaX3qsSkHVRo8VZHV29PQLIzodnZHTMLmXCXafeYw58rsj-upDlQ8YS0PO5cSMWGxG5cdIDktT9M9QWLREsNF9yEIr9OtF4iA9jik2eiDxlCKhBXzXvcWZ8ezofvaAEYUy0SSh-dLs',
    location: { lat: 31.6169, lng: 130.5772 }
  },
  {
    id: 's9',
    name: '天文館通',
    description: '南九州最大の繁華街。ご当地グルメ「白熊」や黒豚料理が楽しめる。',
    area: 'Kagoshima',
    category: 'Food',
    durationMinutes: 120,
    rating: 4.4,
    image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCdz-G_h0k6RJ3ry5mYzbSplIUw_uZ5qvm3fcvKuTI_XYyFKcG68gUEetqtlQsV6_U1xlG079Vpq_TmxVlDP2d2K96Sfhx1rjR-3m6bWu5Ku1CyVc2kxCAgomaqoyXdIumn0GcRGUIXu9M03dG1mDlpgkUnoSxGNOuJkRg14Zn1UxD0jfMbySj3L6sxEdOnU_UuEM0WYzUQm4ddP4z7fnsvSYyZ8lfcSe42HtmUn6qJPpDhy-vShozL-8t_hPBHxrFvo2btn6-mH-U',
    location: { lat: 31.5891, lng: 130.5543 }
  },
  {
    id: 's10',
    name: '霧島神宮',
    description: '天孫降臨神話の主人公を祀る、森の中に佇む朱塗りの美しい社殿。',
    area: 'Kagoshima',
    category: 'History',
    durationMinutes: 60,
    rating: 4.8,
    image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAIE9KY3NbwOR_uiyFxDVZghfvQkwD-MLEiMsYd3OWTd2PZVlugkL73UpjtfuR27PT9dGvsp6yba1AIFSkGvW9u9cVyWC8bNTlZY61SJIv92jn8jRNntaXLuEuyLDlKkMFLSpAAHq0aeUF-QQZE6KdIOnRYPTS4izKkioibuNR3vT83IorS0ejLIGlzO3Vuy2f4auwI2HounBs0OyWvPFsXbCpuE1aaGS6xTTFvICOVyv-2OJJc7dt4PaywbEmrpz9fhKDYDgM02wM',
    location: { lat: 31.8546, lng: 130.8712 }
  }
];

export const plans: Plan[] = [
  {
    id: 'p1',
    title: '京都紅葉ツアー',
    area: 'Kyoto',
    days: 3,
    people: 4,
    budget: 80000,
    createdAt: '2023/10/26',
    thumbnail: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCBEKwjXvH7lYUzUtRXtSkpb47iBWJA4GRSI9dI4bSqBAxSo3JyGGyNwd1txz69Kt7NeNrzHqbCoU6l-mxuTzmrJ9X_V_z-QJpNioTVPRW6jTjT7Mt4vDiwKmHdA0X_tdQSnlwSfB3fj325OaOJuwWgESpJ_mJPsb8UmKrjJ2NiOTxZJ336aROGi7bGf5uy6of28x-uN279dNRmgxb3vOdutZves2NQfdKGiR0c73_qcCBCmmq5bR8m8nLYtkNr3RmkadeBzddHyxI',
    spots: []
  },
  {
    id: 'p2',
    title: 'Tokyo Pop Culture Tour',
    area: 'Tokyo',
    days: 2,
    people: 2,
    budget: 60000,
    createdAt: '2023/11/01',
    thumbnail: 'https://lh3.googleusercontent.com/aida-public/AB6AXuByu9CNi9hOLtjiLiucijbtHgSiJCF6DviVaqhAUWPloauo1vytIhyD2RQuchAOWLCBhwSo0bXC2HAZUt-xxCFEkw5SdMPJRFlCrYEAfYsrJnSxj6AQ5F6wvR73B8IQig5ErAFJhGwgf6vWdl18Hx0XcPCmkrTch_3vpdGQJalTKBokTujisdDxfUHaPHsi4puHmwdxjkReaRs0-k1dhPpwg4q1M7KATonxNU62Bmss_eblgT7JH3VyLc9e03M06iN9aVXLOHvQ1Vk',
    spots: [
      { id: 'ps1', spotId: 's4', spot: spots[3], day: 1, startTime: '09:00', transportMode: 'walk', transportDuration: 15 },
      { id: 'ps2', spotId: 's5', spot: spots[4], day: 1, startTime: '14:30', transportMode: 'train', transportDuration: 30 },
      { id: 'ps3', spotId: 's6', spot: spots[5], day: 2, startTime: '10:00', transportMode: 'train', transportDuration: 20 },
    ]
  },
  {
    id: 'p3',
    title: '東京家族旅行 - 2024年夏',
    area: 'Tokyo',
    days: 3,
    people: 4,
    budget: 150000,
    createdAt: '2024/01/15',
    thumbnail: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBiz9O1N-rC38EKaCKrZkWnHlT3BNZ2_ioD-wgiVPdzSpMhKhO3bsYTdlN2d962ouh2Y6ndN2m2hwwi66cHtF8va1NmQDzbPm6gsD_f3ENFYpul8C5xCQdYyg5L4F2oehZ-RSaX3qsSkHVRo8VZHV29PQLIzodnZHTMLmXCXafeYw58rsj-upDlQ8YS0PO5cSMWGxG5cdIDktT9M9QWLREsNF9yEIr9OtF4iA9jik2eiDxlCKhBXzXvcWZ8ezofvaAEYUy0SSh-dLs',
    spots: [
      { id: 'ps3', spotId: 's5', spot: spots[4], day: 1, startTime: '10:00', transportMode: 'walk', transportDuration: 15, note: '自然を楽しむ' },
      { id: 'ps4', spotId: 's6', spot: spots[5], day: 1, startTime: '13:00', transportMode: 'train', transportDuration: 20, note: '観光' },
    ]
  }
];

export const hotels: Hotel[] = [
  {
    id: 'h1',
    name: 'Sato Hotel Tokyo',
    area: 'Tokyo',
    address: '東京都千代田区',
    pricePerNight: 15000,
    rating: 4.5,
    reviewCount: 1234,
    image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDMjgHh5XErj1TJHzRctMbR89Yvvj-9ka5W6xaF72eWfDbhAdr6wchWnP7tLm308JeN7lqQ8rlXMHKWHE5Cb9lr5bzPzQiYVoyC_FLv1jtQQ6QzZBQ7TcdSoo4qGhYSKSICIY9bCwOnPLto0rYHaTMDiysOu56HglNuUJs3C64YMFCjzY2dJNkgFOIb7Xsgx7uGDpJCDTXwLPFzwVA2PED5GpY-m_mWm8BA70RDj9LvY9iQNj3Y1z9t_4v6fEa8AGnU8CXu9Gmct1o',
    tags: ['駅近', 'ビジネス利用に最適'],
    features: ['Wi-Fi', '朝食付き', '駐車場']
  },
  {
    id: 'h2',
    name: 'Urban Escape Akasaka',
    area: 'Tokyo',
    address: '東京都港区',
    pricePerNight: 25000,
    rating: 4.8,
    reviewCount: 2456,
    image: 'https://lh3.googleusercontent.com/aida-public/AB6AXuBxysaFCq49iaFTD9ChHv6_v960-d4guEv0VwFdmxi7cKtHtPaIka3bjZEASPaaH8RQu9ss6MgccxczvXraFXY9M_ZyF-7JBYtSNzVtDi8dJZj7cDmf8QdQmrzAsISWnHOtENoa2hX6Bd4hujwrE5DLlRdfuKrO7XlW4L24SzqZxChxPWOXVHTkxbxqDTpKnunHuxHYITOGdISbzk6u2y88TnF0nOzFFwjqiMpBbemYFCgBqGLoBVZvRzEkRd6ZVNB4AHTArraj5QU',
    tags: ['カップルにおすすめ'],
    features: ['Wi-Fi', 'プール', '朝食付き']
  }
];

export const adminStats: AdminStat[] = [
  { label: 'プラン生成数 (本日)', value: '1,204', change: '+5.2%', trend: 'up', icon: 'auto_awesome', color: 'text-accent' },
  { label: 'APIコール数 (24h)', value: '8,923', change: '+1.8%', trend: 'up', icon: 'api', color: 'text-primary' },
  { label: 'エラーレート', value: '0.21%', change: '-0.1%', trend: 'down', icon: 'error_outline', color: 'text-red-500' },
];