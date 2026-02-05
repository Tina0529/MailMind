"use client";

import { useState, useEffect } from "react";
import { Skill, api } from "@/lib/api";
import { useLanguage } from "@/lib/LanguageContext";

interface SkillLibraryProps {
  skills: Skill[];
}

// 分类颜色映射
const categoryColors: Record<string, { bg: string; text: string; gradient: string }> = {
  "equipment-fault": { bg: "bg-red-50", text: "text-red-700", gradient: "from-red-400 to-rose-500" },
  "refund-cancellation": { bg: "bg-orange-50", text: "text-orange-700", gradient: "from-orange-400 to-amber-500" },
  "price-inquiry": { bg: "bg-emerald-50", text: "text-emerald-700", gradient: "from-emerald-400 to-teal-500" },
  "technical-support": { bg: "bg-blue-50", text: "text-blue-700", gradient: "from-blue-400 to-indigo-500" },
  "logistics-issue": { bg: "bg-purple-50", text: "text-purple-700", gradient: "from-purple-400 to-violet-500" },
  "complaint-suggestion": { bg: "bg-pink-50", text: "text-pink-700", gradient: "from-pink-400 to-rose-500" },
  "other": { bg: "bg-gray-50", text: "text-gray-700", gradient: "from-gray-400 to-slate-500" },
};

const getCategoryStyle = (category: string) => {
  return categoryColors[category] || categoryColors["other"];
};

interface SourceEmail {
  id: string;
  email_id: string;
  from_address: string;
  from_name: string | null;
  subject: string;
  received_at: string | null;
  category: string | null;
  contribution_type: string;
}

export default function SkillLibrary({ skills }: SkillLibraryProps) {
  const { t } = useLanguage();
  const [expandedSkillId, setExpandedSkillId] = useState<string | null>(null);
  const [sourceEmails, setSourceEmails] = useState<Record<string, SourceEmail[]>>({});
  const [loadingSourceEmails, setLoadingSourceEmails] = useState<string | null>(null);

  // Group skills by category
  const byCategory = skills.reduce((acc, skill) => {
    if (!acc[skill.category]) {
      acc[skill.category] = [];
    }
    acc[skill.category].push(skill);
    return acc;
  }, {} as Record<string, Skill[]>);

  const totalUsage = skills.reduce((sum, s) => sum + s.usage_count, 0);

  const toggleSkill = async (skillId: string) => {
    if (expandedSkillId === skillId) {
      setExpandedSkillId(null);
    } else {
      setExpandedSkillId(skillId);
      // 加载源邮件（如果尚未加载）
      if (!sourceEmails[skillId]) {
        setLoadingSourceEmails(skillId);
        try {
          const result = await api.getSkillSourceEmails(skillId, 5);
          setSourceEmails(prev => ({
            ...prev,
            [skillId]: result.source_emails
          }));
        } catch (error) {
          console.error("Failed to load source emails:", error);
        } finally {
          setLoadingSourceEmails(null);
        }
      }
    }
  };

  return (
    <div className="w-72 bg-[#111820] border-l border-white/10 flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-r from-[#e86803] to-[#ff8c3a] flex items-center justify-center shadow-md">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
            </svg>
          </div>
          <div>
            <h3 className="font-semibold text-[#f8fafc]">{t('skillLibrary')}</h3>
            <p className="text-xs text-[#64748b]">{skills.length} {t('skillsLoaded')}</p>
          </div>
        </div>

        {/* Stats */}
        {skills.length > 0 && (
          <div className="flex gap-2">
            <div className="stat-card primary flex-1">
              <p className="stat-label">{t('categories')}</p>
              <p className="stat-value">{Object.keys(byCategory).length}</p>
            </div>
            <div className="stat-card accent flex-1">
              <p className="stat-label">{t('totalUsage')}</p>
              <p className="stat-value">{totalUsage}</p>
            </div>
          </div>
        )}
      </div>

      {/* Skills List */}
      <div className="flex-1 overflow-y-auto p-3">
        {skills.length === 0 ? (
          <div className="text-center py-8">
            <div className="w-14 h-14 mx-auto mb-3 rounded-2xl bg-[#1a2230] flex items-center justify-center">
              <svg className="w-7 h-7 text-[#64748b]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <p className="text-sm text-[#cbd5e1] font-medium mb-1">{t('noSkillsYet')}</p>
            <p className="text-xs text-[#64748b]">
              {t('syncToGenerateSkills')}
            </p>
          </div>
        ) : (
          <div className="space-y-4">
            {Object.entries(byCategory).map(([category, categorySkills]) => {
              const style = getCategoryStyle(category);
              return (
                <div key={category} className="animate-fadeInUp">
                  {/* Category Header */}
                  <div className="flex items-center gap-2 mb-2">
                    <div className={`w-2 h-2 rounded-full bg-gradient-to-r ${style.gradient}`}></div>
                    <h4 className={`text-xs font-semibold uppercase tracking-wider ${style.text}`}>
                      {category.replace(/-/g, " ")}
                    </h4>
                    <span className="text-xs text-[#64748b]">({categorySkills.length})</span>
                  </div>
                  
                  {/* Skills */}
                  <div className="space-y-2">
                    {categorySkills.map((skill) => {
                      const isExpanded = expandedSkillId === skill.id;
                      return (
                        <div
                          key={skill.id}
                          className={`group p-3 bg-[#1a2230] rounded-xl border border-white/10 hover:border-white/20 cursor-pointer transition-all duration-300 ${isExpanded ? 'ring-2 ring-[#2d91fa]/50' : ''}`}
                          onClick={() => toggleSkill(skill.id)}
                        >
                          {/* Skill Header */}
                          <div className="flex items-center justify-between">
                            <p className="text-sm font-medium text-[#f8fafc] group-hover:text-[#5bb5ff] transition-colors flex-1">
                              {skill.name}
                            </p>
                            <svg
                              className={`w-4 h-4 text-[#64748b] transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </div>

                          <div className="flex items-center justify-between text-xs mt-1.5">
                            <span className="text-[#64748b]">
                              {skill.trigger_keywords.length} {t('keywords')}
                            </span>
                            <div className="flex items-center gap-1.5">
                              <div className={`w-1.5 h-1.5 rounded-full bg-gradient-to-r ${style.gradient}`}></div>
                              <span className={style.text}>{skill.usage_count} {t('usageCount')}</span>
                            </div>
                          </div>

                          {/* Usage Progress Bar */}
                          {totalUsage > 0 && (
                            <div className="mt-2 h-1 bg-white/10 rounded-full overflow-hidden">
                              <div
                                className={`h-full bg-gradient-to-r ${style.gradient} transition-all duration-500`}
                                style={{ width: `${Math.max((skill.usage_count / totalUsage) * 100, 5)}%` }}
                              ></div>
                            </div>
                          )}

                          {/* Expanded Details */}
                          {isExpanded && (
                            <div className="mt-4 pt-3 border-t border-white/10 space-y-3 animate-fadeInUp">
                              {/* Description */}
                              {skill.description && (
                                <div>
                                  <p className="text-xs font-semibold text-[#5bb5ff] mb-1">{t('skillDescription')}</p>
                                  <p className="text-xs text-[#cbd5e1] leading-relaxed">{skill.description}</p>
                                </div>
                              )}

                              {/* Trigger Keywords */}
                              {skill.trigger_keywords.length > 0 && (
                                <div>
                                  <p className="text-xs font-semibold text-[#ff8c3a] mb-1.5">{t('triggerKeywords')}</p>
                                  <div className="flex flex-wrap gap-1">
                                    {skill.trigger_keywords.slice(0, 6).map((kw, idx) => (
                                      <span
                                        key={idx}
                                        className="px-2 py-0.5 text-xs bg-[#e86803]/20 text-[#ff8c3a] rounded-full"
                                      >
                                        {kw}
                                      </span>
                                    ))}
                                    {skill.trigger_keywords.length > 6 && (
                                      <span className="px-2 py-0.5 text-xs bg-white/10 text-[#64748b] rounded-full">
                                        +{skill.trigger_keywords.length - 6} {t('more')}
                                      </span>
                                    )}
                                  </div>
                                </div>
                              )}

                              {/* Rules */}
                              {skill.rules && skill.rules.length > 0 && (
                                <div>
                                  <p className="text-xs font-semibold text-[#4ade80] mb-1.5">{t('processingRules')}</p>
                                  <div className="space-y-2">
                                    {skill.rules.slice(0, 3).map((rule: any, idx: number) => (
                                      <div key={idx} className="bg-white/5 rounded-lg p-2">
                                        <p className="text-xs font-medium text-[#cbd5e1] mb-1">
                                          {rule.name || `${t('rule')} ${idx + 1}`}
                                        </p>
                                        {rule.action_steps && (
                                          <ul className="text-xs text-[#64748b] space-y-0.5">
                                            {rule.action_steps.slice(0, 2).map((step: string, stepIdx: number) => (
                                              <li key={stepIdx} className="flex items-start gap-1">
                                                <span className="text-[#4ade80]">•</span>
                                                <span className="line-clamp-2">{step}</span>
                                              </li>
                                            ))}
                                          </ul>
                                        )}
                                      </div>
                                    ))}
                                    {skill.rules.length > 3 && (
                                      <p className="text-xs text-[#64748b] text-center">
                                        {t('moreRules').replace('{count}', String(skill.rules.length - 3))}
                                      </p>
                                    )}
                                  </div>
                                </div>
                              )}

                              {/* Stats */}
                              <div className="flex gap-2 pt-2">
                                <div className="flex-1 bg-white/5 rounded-lg p-2 text-center">
                                  <p className="text-xs text-[#64748b]">{t('successRate')}</p>
                                  <p className="text-sm font-bold text-[#4ade80]">
                                    {skill.usage_count > 0
                                      ? `${Math.round((skill.success_count / skill.usage_count) * 100)}%`
                                      : '-'}
                                  </p>
                                </div>
                                <div className="flex-1 bg-white/5 rounded-lg p-2 text-center">
                                  <p className="text-xs text-[#64748b]">{t('status')}</p>
                                  <p className={`text-sm font-bold ${skill.is_active ? 'text-[#4ade80]' : 'text-[#64748b]'}`}>
                                    {skill.is_active ? t('enabled') : t('disabled')}
                                  </p>
                                </div>
                              </div>

                              {/* Source Emails - 技能来源追溯 */}
                              <div className="pt-3 border-t border-white/10 mt-3">
                                <p className="text-xs font-semibold text-[#5bb5ff] mb-2">{t('sourceEmails')}</p>
                                {loadingSourceEmails === skill.id ? (
                                  <div className="flex items-center justify-center py-2">
                                    <svg className="w-4 h-4 animate-spin text-[#5bb5ff]" fill="none" viewBox="0 0 24 24">
                                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                                    </svg>
                                    <span className="text-xs text-[#64748b] ml-2">{t('loading')}</span>
                                  </div>
                                ) : sourceEmails[skill.id]?.length > 0 ? (
                                  <div className="space-y-1.5">
                                    {sourceEmails[skill.id].slice(0, 3).map((email) => (
                                      <div key={email.id} className="bg-white/5 rounded-lg p-2">
                                        <p className="text-xs text-[#cbd5e1] truncate font-medium">
                                          {email.subject}
                                        </p>
                                        <div className="flex items-center gap-2 mt-1">
                                          <span className="text-xs text-[#64748b] truncate">
                                            {email.from_name || email.from_address}
                                          </span>
                                          <span className="text-xs px-1.5 py-0.5 bg-[#2d91fa]/20 text-[#5bb5ff] rounded">
                                            {email.contribution_type === 'initial_learning' ? t('initialLearning') : t('evolution')}
                                          </span>
                                        </div>
                                      </div>
                                    ))}
                                    {sourceEmails[skill.id].length > 3 && (
                                      <p className="text-xs text-[#64748b] text-center">
                                        {t('moreSourceEmails').replace('{count}', String(sourceEmails[skill.id].length - 3))}
                                      </p>
                                    )}
                                  </div>
                                ) : (
                                  <p className="text-xs text-[#64748b] text-center py-2">
                                    {t('noSourceEmails')}
                                  </p>
                                )}
                              </div>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
