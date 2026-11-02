"use client";

import Link from "next/link";
import { useState } from "react";
import type { QuizBlock } from "@/lib/extras";

export default function QuizClient({
  courseKey,
  title,
  intro,
  blocks,
}: {
  courseKey: string;
  title: string;
  intro: string;
  blocks: QuizBlock[];
}) {
  const [blockIndex, setBlockIndex] = useState(0);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [picked, setPicked] = useState<number | null>(null);
  const [checked, setChecked] = useState(false);
  const [score, setScore] = useState(0);
  const [finished, setFinished] = useState(false);

  const block = blocks[blockIndex];
  const question = block.questions[questionIndex];
  const total = block.questions.length;
  const isLast = questionIndex === total - 1;
  const isCorrect = checked && picked === question.answer;
  const progress = finished
    ? 100
    : ((questionIndex + (checked ? 1 : 0)) / total) * 100;

  function resetBlock(nextBlock = blockIndex) {
    setBlockIndex(nextBlock);
    setQuestionIndex(0);
    setPicked(null);
    setChecked(false);
    setScore(0);
    setFinished(false);
  }

  function submit() {
    if (picked === null || checked) return;
    setChecked(true);
    if (picked === question.answer) setScore((value) => value + 1);
  }

  function next() {
    if (!checked) return;
    if (isLast) {
      setFinished(true);
      return;
    }
    setQuestionIndex((value) => value + 1);
    setPicked(null);
    setChecked(false);
  }

  function optionClass(index: number) {
    if (!checked) return picked === index ? "quiz-option is-selected" : "quiz-option";
    if (index === question.answer) return "quiz-option is-correct";
    if (index === picked) return "quiz-option is-wrong";
    return "quiz-option is-dim";
  }

  return (
    <div className="quiz-shell">
      <div className="quiz-topline">
        <Link href={`/course/${courseKey}/`} className="quiz-back">
          ← 返回课程
        </Link>
        <span>{total * blocks.length} 道题 · 单选</span>
      </div>

      <header className="quiz-hero">
        <p className="quiz-kicker">面试题库</p>
        <h1>{title}</h1>
        <p>{intro}</p>
      </header>

      <div className="quiz-blocks" role="tablist" aria-label="题库板块">
        {blocks.map((item, index) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={index === blockIndex}
            className={`quiz-block-tab ${index === blockIndex ? "active" : ""}`}
            onClick={() => resetBlock(index)}
          >
            <span>{item.name}</span>
            <small>{item.range} · {item.questions.length} 题</small>
          </button>
        ))}
      </div>

      <div className="quiz-progress" aria-hidden>
        <i style={{ width: `${progress}%` }} />
      </div>

      {finished ? (
        <section className="quiz-result" aria-live="polite">
          <span className="quiz-result-label">本板块完成</span>
          <strong>
            {score}
            <em> / {total}</em>
          </strong>
          <p>
            {score === total
              ? "全对。这个板块的概念已经比较扎实，可以换个板块继续。"
              : score >= Math.ceil(total * 0.75)
                ? "基础不错，建议重点回看错题解析里的边界条件。"
                : "建议先回到对应章节补一遍概念，再重做这一组题。"}
          </p>
          <div className="quiz-result-actions">
            <button type="button" className="btn-primary border-0" onClick={() => resetBlock()}>
              再做一遍
            </button>
            <Link href={`/course/${courseKey}/`} className="btn-ghost no-underline">
              回到课程目录
            </Link>
          </div>
        </section>
      ) : (
        <section className="quiz-card" aria-live="polite">
          <div className="quiz-meta">
            <span>{block.name}</span>
            <span>
              第 {questionIndex + 1} / {total} 题
            </span>
          </div>
          <h2>{question.q}</h2>

          <div className="quiz-options">
            {question.options.map((option, index) => (
              <button
                key={option}
                type="button"
                className={optionClass(index)}
                disabled={checked}
                aria-pressed={picked === index}
                onClick={() => setPicked(index)}
              >
                <span className="quiz-option-key">{String.fromCharCode(65 + index)}</span>
                <span>{option}</span>
                {checked && index === question.answer && (
                  <span className="quiz-option-mark">正确答案</span>
                )}
                {checked && index === picked && index !== question.answer && (
                  <span className="quiz-option-mark">你的选择</span>
                )}
              </button>
            ))}
          </div>

          {checked && (
            <div className={`quiz-feedback ${isCorrect ? "ok" : "bad"}`}>
              <strong>{isCorrect ? "答对了" : "这题选错了"}</strong>
              <p>{question.explain}</p>
            </div>
          )}

          <div className="quiz-actions">
            <span className="quiz-actions-hint">
              {checked ? "看完解析再进入下一题" : "选一个最符合工程实践的答案"}
            </span>
            {!checked ? (
              <button
                type="button"
                className="btn-primary border-0 disabled:opacity-40"
                disabled={picked === null}
                onClick={submit}
              >
                提交答案
              </button>
            ) : (
              <button type="button" className="btn-primary border-0" onClick={next}>
                {isLast ? "查看成绩" : "下一题"}
              </button>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
